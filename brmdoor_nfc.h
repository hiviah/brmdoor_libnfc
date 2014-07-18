#pragma once

#include <string>

class NFCDevice
{

public:
    
    NFCDevice();
    
    ~NFCDevice() {}

    std::string scanUID();
};
