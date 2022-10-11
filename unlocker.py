import time

class Unlocker(object):
    """Abstract class/interface for Unlocker object.
    Unlocker useful for simulation, but does not actually unlock any lock.
    """
    def __init__(self, config):
        """
        Creates unlocked instance from config, where section named after
        the class is supposed to exist.
        
        @param config: BrmdoorConfig instance
        """
        self.config = config.config
        self.lockOpenedSecs = config.lockOpenedSecs
        self.unlockerName = type(self).__name__
    
    def unlock(self):
        """Unlock lock for given self.lockOpenedSecs.
        In this class case, it's only simulated
        """
        time.sleep(self.lockOpenedSecs)

    def lock(self):
        """
        Lock the lock back. Meant to be used when program is shut down
        so that lock is not left disengaged.
        """
        pass


class UnlockerWiringPi(Unlocker):
    """Uses configured pings via WiringPi to open lock.
    """

    def __init__(self, config):
        import wiringpi
        Unlocker.__init__(self, config)
        # PIN numbers follow P1 header BCM GPIO numbering, see https://projects.drogon.net/raspberry-pi/wiringpi/pins/
        # Local copy of the P1 in repo mapping see gpio_vs_wiringpi_numbering_scheme.png.
        wiringpi.wiringPiSetupGpio()
        self.lockPin = self.config.getint("UnlockerWiringPi", "lock_pin")
        wiringpi.pinMode(self.lockPin, wiringpi.OUTPUT) #output
    
    def unlock(self):
        """Unlocks lock at configured pin by pulling it high.
        """
        import wiringpi
        wiringpi.digitalWrite(self.lockPin, 1)
        time.sleep(self.lockOpenedSecs)
        wiringpi.digitalWrite(self.lockPin, 0)

    def lock(self):
        """
        Lock the lock back. Meant to be used when program is shut down
        so that lock is not left disengaged.
        """
        import wiringpi
        wiringpi.digitalWrite(self.lockPin, 0)

