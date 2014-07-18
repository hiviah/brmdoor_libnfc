#include <string>

#include <nfc/nfc.h>
#include <nfc/nfc-types.h>


#include "brmdoor_nfc.h"

using namespace std;

NFCDevice::NFCDevice()
{
    pollNr = 20;
    pollPeriod = 2;
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


