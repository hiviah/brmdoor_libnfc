#include <string>

#include <nfc/nfc.h>
#include <nfc/nfc-types.h>


#include "brmdoor_nfc.h"

using namespace std;

NFCDevice::NFCDevice()
{
    pollNr = 20;
    pollPeriod = 2;

    _nfcContext = NULL;

    nfc_init(&_nfcContext);
    if (_nfcContext == NULL) {
        throw NFCError("Unable to init libnfc (malloc)");
    }

    _nfcDevice = nfc_open(_nfcContext, NULL);

    if (_nfcDevice == NULL) {
        throw NFCError("Unable to open NFC device.");
    }

    if (nfc_initiator_init(_nfcDevice) < 0) {
        nfc_close(_nfcDevice);
        throw NFCError("NFC initiator error");
    }

}

NFCDevice::~NFCDevice()
{
    nfc_exit(_nfcContext);
}

std::string NFCDevice::scanUID()
{
    return "1234";
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
