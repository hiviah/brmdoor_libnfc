#pragma once

#include <string>
#include <inttypes.h>
#include <stdexcept>

#include <nfc/nfc.h>
#include <nfc/nfc-types.h>

/** 
 * Exception class for reader related errors. 
 */
class NFCError: public std::exception
{

public:

    /** Constructor with human-readable reason message */
    NFCError(const std::string& msg);
    
    /** Returns reason why this was thrown. */
    const char *what() const throw() {return _msg.c_str();}

    ~NFCError() throw() {}

protected:

    /** Reason message */
    std::string _msg;
};

/**
 * Represents response APDU for ISO14443-4.
 */
class ResponseAPDU
{
public:
    
    /** Parse response APDU from raw data */
    ResponseAPDU(const std::string& data);
    
    ~ResponseAPDU() {}
    
    /** Return whole status word */
    uint16_t sw() const {return _sw;}
    
    /** Return first byte of status word */
    uint8_t sw1() const {return _sw >> 8;}
    
    /** Return second byte of status word */
    uint8_t sw2() const {return _sw & 0xFF;}
    
    /** Return whether this is properly formed response */
    bool valid() const {return _valid;}
    
    /** Returns APDU data */
    const std::string& data() const {return _data;}

private:
    
    /** Data from response, without SW1 and SW2 */
    std::string _data;
    
   /** SW1 and SW2 */ 
    uint16_t _sw;
    
   /** Whether response APDU has had enough data to be valid */ 
    bool _valid;
};

/**
 * Represents one PN532 reader device. Config is taken from default
 * libnfc-specified location. That usually means first device found is used.
 *
 * Config resides in /etc/nfc/libnfc.conf if installed from packages or
 * /usr/local/etc/nfc/libnfc.conf if installed from source.
 *
 * A device is specified like this:
 *
 * device.connstring = pn532_uart:/dev/ttyACM0
 * device.connstring = "pn532_spi:/dev/spidev0.0"
 *
 * Refer to libnfc documentation for setting up devices.
 */
class NFCDevice
{

public:
    
    /** 
     * Initializes PN53x libnfc device and opens it, so you don't need to call
     * open() after constructor.
     *
     * @throws NFCError if no device found or communication failed
     */
    NFCDevice() throw(NFCError);
    
    /** Destructor frees internal libnfc structures */
    virtual ~NFCDevice();

    /** 
     * Read UID of a card in field. If multiple cards are found, return UID of first one.
     *
     * If you are polling for cards with this, include some sleep in-between the calls (e.g. 0.1 sec).
     * 
     * @returns binary string containing UID or empty if non-supported card
     *          present in reader field
     * @throws NFCError if no cards in reader's field
     */
    std::string scanUID() throw(NFCError);
    
    /**
     * Wait for one passive or emulated target and select it by reader.
     */
    void selectPassiveTarget() throw(NFCError);
    
    /**
     * Send APDU to passive or emulated target. The target must be already
     * selected by selectPassiveTarget() or scanUID().
     *
     * @param apdu command APDU to send
     * @param returns response APDU received from target
     * @throws NFCError if response APDU is too long or couldn't send APDU
     */
    ResponseAPDU sendAPDU(const std::string& apdu) throw(NFCError);

    /**
     * Read NDEF message from Desfire.
     *
     * @returns NDEF message or empty string if there wasn't message
     * @throws NFCError if there was problem communication with card or couldn't authenticate
     */
    std::string readDesfireNDEF() throw(NFCError);

    /** Open device explicitly. May be useful after explicit close */
    void open() throw(NFCError);

    /** Returns true iff device was opened and not unloaded. */
    bool opened() const {return _opened && !_unloaded;}

    /** Close reader. You need to reopen before reading again */
    void close();

    /** 
     * Unload all structures, close device. It's kind of explicit destructor
     * since we can't be sure the destructor will be called in Python.
     */
    void unload();

    /** 
     * Specifies the number of polling (0x01 – 0xFE: 1 up to 254 polling, 0xFF:
     * Endless polling)
     */
    uint8_t pollNr;

    /** 
     * Polling period when waiting for card in multiples of 150 ms.
     * (0x01 – 0x0F: 150ms – 2.25s)
     */
    uint8_t pollPeriod;
    
    /**
     * Timeout for waiting response to sent APDU. Value -1 means wait forever.
     */
    int apduTimeout;

protected:

    /** Modulations that specify cards accepted by reader */
    static const nfc_modulation _modulations[5];

    /** Number of modulations in _modulations array */
    static const size_t _modulationsLen;

    /** libnfc-specific opaque context */
    nfc_context *_nfcContext;

    /** Device opened by libnfc functions, may be NULL */
    nfc_device *_nfcDevice;

    /** Whether device has been successfully opened */
    bool _opened;

    /** Whether device and its internal libnfc structures have been unloaded */
    bool _unloaded;

};


