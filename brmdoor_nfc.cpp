#include <string>
#include <cassert>

#include <nfc/nfc.h>
#include <nfc/nfc-types.h>


#include "brmdoor_nfc.h"

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

    res = nfc_initiator_poll_target(_nfcDevice, _modulations, _modulationsLen, pollNr, pollPeriod, &nt);
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
