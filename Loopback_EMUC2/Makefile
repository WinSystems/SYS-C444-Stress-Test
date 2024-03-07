

:= @
CC              := aarch64-unknown-linux-gnu-gcc -std=gnu99
SRCS            := $(wildcard *.c)
OBJS_64         := $(SRCS:.c=.o64)
TARGET_64       := emuc_64
LIBS_64         := lib_emuc2_64.a -lpthread -lm
CFLAGS_64       := -Wall -I ./include -fPIC -shared
LDFLAGS_64      := $(LIBS_64)

############################################
.PHONY: all both clean

all: loopback.so

############################################

loopback.so: loopback.c Makefile
	$(Q)echo "  Compiling '$<' ..."
	$(Q)$(CC) $(CFLAGS_64) $(LIBS_64) -o $@ $<

clean:
	$(Q)rm -f .depend *~ *.bak *.res *.o64 *.so *.o64
	$(Q)echo "  Cleaning '$(TARGET_64)' ..."
	$(Q)rm -f $(TARGET_64)
