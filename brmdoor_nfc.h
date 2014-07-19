#pragma once

#include <string>
#include <inttypes.h>
#include <stdexcept>

#include <nfc/nfc.h>
#include <nfc/nfc-types.h>

class NFCDevice
{

public:
    
    NFCDevice();
    
    virtual ~NFCDevice();

    std::string scanUID();

    uint8_t pollNr;

    uint8_t pollPeriod;

protected:

    static const nfc_modulation _modulations[5];    

    static const size_t _modulationsLen = 5;

    nfc_context *_nfcContext;

    nfc_device *_nfcDevice;

};


class NFCError: public std::exception
{

public:

    NFCError(const std::string& msg);
    
    const char *what() const throw() {return _msg.c_str();}

    ~NFCError() throw() {}

protected:

    std::string _msg;
};

