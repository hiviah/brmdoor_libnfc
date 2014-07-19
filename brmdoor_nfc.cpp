#include <string>

#include <nfc/nfc.h>
#include <nfc/nfc-types.h>


#include "brmdoor_nfc.h"

using namespace std;

NFCDevice::NFCDevice() throw(NFCError):
    pollNr(20),
    pollPeriod(2),
    _nfcContext(NULL),
    _nfcDevice(NULL),
    _opened(false)
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
    nfc_exit(_nfcContext);
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

    nfc_close(_nfcDevice);
    _nfcDevice = NULL;
    _opened = false;
}

std::string NFCDevice::scanUID() throw(NFCError)
{
    int res;
    nfc_target nt;

    res = nfc_initiator_poll_target(_nfcDevice, _modulations, _modulationsLen, pollNr, pollPeriod, &nt);
    if (res < 0) {
        throw NFCError("NFC polling error");
    }

    // we are not interested in non-ISO-14443A cards
    if (nt.nm.nmt != NMT_ISO14443A) {
        return "";
    }

    const nfc_iso14443a_info& nai = nt.nti.nai;

    return string((const char*)nai.abtUid, nai.szUidLen);
}

const nfc_modulation NFCDevice::_modulations[5] = {
        { /*.nmt = */ NMT_ISO14443A, /* .nbr = */ NBR_106 },
        { /*.nmt = */ NMT_ISO14443B, /* .nbr = */ NBR_106 },
        { /*.nmt = */ NMT_FELICA,    /* .nbr = */ NBR_212 },
        { /*.nmt = */ NMT_FELICA,    /* .nbr = */ NBR_424 },
        { /*.nmt = */ NMT_JEWEL,     /* .nbr = */ NBR_106 },
    };
    
const size_t _modulationsLen = 5;


NFCError::NFCError(const std::string& msg)
{
    _msg = msg;
}
