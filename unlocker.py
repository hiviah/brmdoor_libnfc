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
        import wiringpi2 as wiringpi
        Unlocker.__init__(self, config)
        wiringpi.wiringPiSetupGpio() # pin numbers follow P1 GPIO header
        self.lockPin = self.config.getint("UnlockerWiringPi", "lock_pin")
        wiringpi.pinMode(self.lockPin, 1) #output
    
    def unlock(self):
        """Unlocks lock at configured pin by pulling it high.
        """
        import wiringpi2 as wiringpi
        wiringpi.digitalWrite(self.lockPin, 1)
        time.sleep(self.lockOpenedSecs)
        wiringpi.digitalWrite(self.lockPin, 0)

    def lock(self):
        """
        Lock the lock back. Meant to be used when program is shut down
        so that lock is not left disengaged.
        """
        import wiringpi2 as wiringpi
        wiringpi.digitalWrite(self.lockPin, 0)

