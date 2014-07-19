# Brmdoor via libnfc

This is an access-control system implementation via contactless ISO 14443A cards
and a PN53x-based reader. So you basically swipe your card, and if it's in
database, the door unlocks.

It's primarily intended for Raspberry Pi, but can work for other plaforms that
can work with libnfc (including common x86 systems).

## Aims

People have made few implementations that kind of work
[1](https://www.brmlab.cz/project/brmdoor),
[2](https://github.com/hiviah/brmdoor-pn532/tree/pn532), but are
messy - either due to limitations of hardware or plagued by having to simulate
backward compatbility errors.

So we need and have:

  - clean, documented C++ code and swig wrapper interfacing libnfc directly
  - clean, documented Python code
  - documentation (doxygen)
  - sqlite support - no need to recompile for access control list change, just
    edit the sqlite database
  - extensibility

## Howto

...will be done once all the scripts are finished.
