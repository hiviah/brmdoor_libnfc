#pragma once

#include <string>
#include <inttypes.h>

#include <nfc/nfc.h>
#include <nfc/nfc-types.h>

class NFCDevice
{

public:
    
    NFCDevice();
    
    ~NFCDevice() {}

    std::string scanUID();

    uint8_t pollNr;

    uint8_t pollPeriod;

protected:

    static const nfc_modulation _modulations[5];    
    static const size_t _modulationsLen = 5;

};
