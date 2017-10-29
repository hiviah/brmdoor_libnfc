#include <string>
#include <cassert>
#include <memory>

#include <Python.h>

#include <nfc/nfc.h>
#include <nfc/nfc-types.h>
#include <freefare.h>

#include "nfc_smartcard.h"

using namespace std;

ResponseAPDU::ResponseAPDU(const string &data)
{
    size_t len = data.size();
    _valid = len >= 2;
    
    if (!_valid) {
	return; 
    }
    
    _sw = (uint8_t(data[len-2]) << 8) | uint8_t(data[len-1]);
    _data = data.substr(0, len-2);
}

NFCDevice::NFCDevice() throw(NFCError):
    pollNr(20),
    pollPeriod(2),
    apduTimeout(500),
    _nfcContext(NULL),
    _nfcDevice(NULL),
    _opened(false),
    _unloaded(false)
{
    nfc_init(&_nfcContext);
    if (_nfcContext == NULL) {
        throw NFCError("Unable to init libnfc (malloc)");
    }

    open();
}

NFCDevice::~NFCDevice()
{
    close();
    unload();
}

void NFCDevice::open() throw(NFCError)
{
    if (opened()) {
        return;
    }

    _nfcDevice = nfc_open(_nfcContext, NULL);

    if (_nfcDevice == NULL) {
        throw NFCError("Unable to open NFC device.");
    }

    _opened = true;

    if (nfc_initiator_init(_nfcDevice) < 0) {
        close();
        throw NFCError("NFC initiator error");
    }
}

void NFCDevice::close()
{
    if (!opened()) {
        return;
    }

    assert(_nfcDevice);

    nfc_close(_nfcDevice);
    _nfcDevice = NULL;
    _opened = false;
}

void NFCDevice::unload()
{
    if (_unloaded) {
        return;
    }

    assert(_nfcContext);

    nfc_exit(_nfcContext);
    _nfcContext = NULL;
    _unloaded = true;
}

std::string NFCDevice::scanUID() throw(NFCError)
{
    int res;
    nfc_target nt;
    string uid;

    if (!opened()) {
        throw NFCError("NFC device not opened");
    }

    Py_BEGIN_ALLOW_THREADS
    res = nfc_initiator_poll_target(_nfcDevice, _modulations, _modulationsLen, pollNr, pollPeriod, &nt);
    Py_END_ALLOW_THREADS

    if (res < 0) {
        throw NFCError("NFC polling error");
    }

    // we are not interested in non-ISO-14443A cards
    if (nt.nm.nmt != NMT_ISO14443A) {
        return string();
    }

    const nfc_iso14443a_info& nai = nt.nti.nai;
    uid = string((const char*)nai.abtUid, nai.szUidLen);

//    nfc_initiator_deselect_target(_nfcDevice);

    return uid;
}

void NFCDevice::selectPassiveTarget() throw(NFCError)
{
    nfc_target nt;
    while (nfc_initiator_select_passive_target(_nfcDevice, _modulations[0], NULL, 0, &nt) <= 0);
}

ResponseAPDU NFCDevice::sendAPDU(const string &apdu) throw(NFCError)
{
    int res;
    uint8_t rapdu[512];
    
    if ((res = nfc_initiator_transceive_bytes(_nfcDevice, (uint8_t*)apdu.data(), apdu.size(),  
                                              rapdu, 512, apduTimeout)) < 0) {
	if (res == NFC_EOVFLOW) {
	    throw NFCError("Response APDU too long");
	}
	
	throw NFCError("Failed to transceive APDU");
    } else {
	string rapduData((char *)rapdu, res);
      	ResponseAPDU responseApdu(rapduData);
	
	if (!responseApdu.valid()) {
	    throw NFCError("Invalid response APDU was received");
	}
	
	return responseApdu;
    }
}

std::string NFCDevice::readDesfireNDEF() throw(NFCError)
{
    uint8_t key_data_app[8]  = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 }; //auth key
    int res;
    uint16_t  ndef_msg_len;

    std::unique_ptr<MifareTag, std::function<void(MifareTag*)> > tags = {freefare_get_tags (_nfcDevice), freefare_free_tags};
    if (!tags) {
        throw NFCError("No tags detected");
    }
    MifareTag& tag = *tags; //only first one is used

    if (DESFIRE != freefare_get_tag_type (tag)) {
        throw NFCError("Tag is not a Desfire tag");
    }

    res = mifare_desfire_connect (tag);
    if (res < 0) {
        throw NFCError("Can't connect to Mifare DESFire target.");
    }

    // We've to track DESFire version as NDEF mapping is different
    struct mifare_desfire_version_info info;
    res = mifare_desfire_get_version (tag, &info);
    if (res < 0) {
        throw NFCError("Error getting Desfire version");
    }

    std::unique_ptr<mifare_desfire_key, std::function<void(MifareDESFireKey)> > key_app{mifare_desfire_des_key_new_with_version (key_data_app),
                                                                                      mifare_desfire_key_free};

    // Mifare DESFire SelectApplication (Select application)
    MifareDESFireAID aid;
    if (info.software.version_major==0) {
        aid = mifare_desfire_aid_new(0xEEEE10);
    } else {
        // There is no more relationship between DESFire AID and ISO AID...
        // Let's assume it's in AID 000001h as proposed in the spec
        aid = mifare_desfire_aid_new(0x000001);
    }

    res = mifare_desfire_select_application(tag, aid);
    if (res < 0)
        throw NFCError("Application selection failed. NDEF message might not have been created yet.");
    free (aid);

    // Authentication with NDEF Tag Application master key (Authentication with key 0)
    res = mifare_desfire_authenticate (tag, 0, key_app.get());
    if (res < 0)
        throw NFCError("Authentication with NDEF Tag Application master key failed");

    // Read Capability Container file E103
    uint8_t lendata[20]; // cf FIXME in mifare_desfire.c read_data()
    if (info.software.version_major==0)
        res = mifare_desfire_read_data (tag, 0x03, 0, 2, lendata);
    else
        // There is no more relationship between DESFire FID and ISO FileID...
        // Let's assume it's in FID 01h as proposed in the spec
        res = mifare_desfire_read_data (tag, 0x01, 0, 2, lendata);
    if (res < 0)
        throw NFCError("Read CC len failed");
    uint16_t cclen = (((uint16_t) lendata[0]) << 8) + ((uint16_t) lendata[1]);
    if (cclen < 15)
        throw NFCError("CC too short IMHO");
    std::unique_ptr<uint8_t[]> cc_data{new uint8_t[cclen+20]};
    if (info.software.version_major==0)
        res = mifare_desfire_read_data (tag, 0x03, 0, cclen, cc_data.get());
    else
        res = mifare_desfire_read_data (tag, 0x01, 0, cclen, cc_data.get());
    if (res < 0)
        throw NFCError("Read CC data failed");
    // Search NDEF File Control TLV
    uint8_t off = 7;
    while (((off+7) < cclen) && (cc_data[off] != 0x04)) {
        // Skip TLV
        off += cc_data[off+1] + 2;
    }
    if (off+7 >= cclen)
        throw NFCError("CC does not contain expected NDEF File Control TLV");
    if (cc_data[off+2] != 0xE1)
        throw NFCError("Unknown NDEF File reference in CC");
    uint8_t file_no;
    if (info.software.version_major==0)
        file_no = cc_data[off+3];
    else
        // There is no more relationship between DESFire FID and ISO FileID...
        // Let's assume it's in FID 02h as proposed in the spec
        file_no = 2;
    uint16_t ndefmaxlen = (((uint16_t) cc_data[off+4]) << 8) + ((uint16_t) cc_data[off+5]);
    std::unique_ptr<uint8_t[]> ndef_msg{new uint8_t[ndefmaxlen+20]}; // cf FIXME in mifare_desfire.c read_data()

    res = mifare_desfire_read_data (tag, file_no, 0, 2, lendata);
    if (res < 0)
        throw NFCError("Read NDEF len failed");
    ndef_msg_len = (((uint16_t) lendata[0]) << 8) + ((uint16_t) lendata[1]);
    if (ndef_msg_len + 2 > ndefmaxlen)
        throw NFCError("Declared NDEF size larger than max NDEF size");
    res = mifare_desfire_read_data (tag, file_no, 2, ndef_msg_len, ndef_msg.get());
    if (res < 0)
        throw NFCError("Read data failed");
    std::string result{(char*)ndef_msg.get(), ndef_msg_len};

    mifare_desfire_disconnect (tag);
    return result;
}


const nfc_modulation NFCDevice::_modulations[5] = {
        { /*.nmt = */ NMT_ISO14443A, /* .nbr = */ NBR_106 }
        //{ /*.nmt = */ NMT_ISO14443B, /* .nbr = */ NBR_106 },
        //{ /*.nmt = */ NMT_FELICA,    /* .nbr = */ NBR_212 },
        //{ /*.nmt = */ NMT_FELICA,    /* .nbr = */ NBR_424 },
        //{ /*.nmt = */ NMT_JEWEL,     /* .nbr = */ NBR_106 },
    };
    
const size_t NFCDevice::_modulationsLen = 1;


NFCError::NFCError(const std::string& msg)
{
    _msg = msg;
}
