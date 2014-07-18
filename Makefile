CXXFLAGS += -Wall -g -I /usr/include/python2.6/ -fPIC
LDFLAGS += -lnfc
OBJECTS = brmdoor_nfc.o brmdoor_nfc_wrap.o
PY_MODULE = _brmdoor_nfc.so

all: $(PY_MODULE)

$(PY_MODULE): $(OBJECTS)
	g++ -shared -o $@ $(OBJECTS) $(LDFLAGS)

brmdoor_nfc.o: brmdoor_nfc.cpp brmdoor_nfc.h
	g++ -c $(CXXFLAGS) brmdoor_nfc.cpp

brmdoor_nfc_wrap.o: brmdoor_nfc_wrap.cxx
	g++ -c $(CXXFLAGS) $<

brmdoor_nfc_wrap.cxx: brmdoor_nfc.i
	swig -python -c++ $<

clean:
	rm -f $(OBJECTS) $(PY_MODULE)
