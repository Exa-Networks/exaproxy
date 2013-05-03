# encoding: utf-8

# from https://gist.github.com/NicolasT/4519146

'''
Demonstration of using splice from Python

This code starts a TCP/IP server, waits for a connection, and once a connection
has been made, launches a subprocess ('cat' of this file). Then, it transfers
everything this subprocess outputs on stdout to the socket client. When no more
data is available, everything is shut down.

The server is fully blocking etc. etc. etc. even though splice(2) supports
non-blocking execution. You should set any pipes to non-blocking mode (using
fcntl or whatever) and call splice with the `SPLICE_F_NONBLOCK` flag set, then
integrate FD read/write'ability with your mainloop and select/poll/epoll/...
calls. This is very application/framework/library-specific, so I don't bother
with it in this code. Notice you might need to wrap calls to splice in an
exception handler to catch EWOULDBLOCK, EAGAIN,... The lot.

Bindings to splice(2) are made using ctypes.

This code is public domain as fully as possible in any applicable law, etc. etc.
etc.

It comes without warranty blah blah blah do whatever you want with it but don't
blame me if anything breaks.

If you find any errors, please let me know!
'''

import os
import os.path
import errno
import socket
import subprocess

import ctypes
import ctypes.util

def make_splice():
    '''Set up a splice(2) wrapper'''

    # Load libc
    libc_name = ctypes.util.find_library('c')
    libc = ctypes.CDLL(libc_name, use_errno=True)

    # Get a handle to the 'splice' call
    c_splice = libc.splice

    # These should match for x86_64, might need some tweaking for other
    # platforms...
    c_loff_t = ctypes.c_uint64
    c_loff_t_p = ctypes.POINTER(c_loff_t)

    # ssize_t splice(int fd_in, loff_t *off_in, int fd_out,
    #     loff_t *off_out, size_t len, unsigned int flags)
    c_splice.argtypes = [
        ctypes.c_int, c_loff_t_p,
        ctypes.c_int, c_loff_t_p,
        ctypes.c_size_t,
        ctypes.c_uint
    ]
    c_splice.restype = ctypes.c_ssize_t

    # Clean-up closure names. Yup, useless nit-picking.
    del libc
    del libc_name
    del c_loff_t_p

    # pylint: disable-msg=W0621,R0913
    def splice(fd_in, off_in, fd_out, off_out, len_, flags):
        '''Wrapper for splice(2)

        See the syscall documentation ('man 2 splice') for more information
        about the arguments and return value.

        `off_in` and `off_out` can be `None`, which is equivalent to `NULL`.

        If the call to `splice` fails (i.e. returns -1), an `OSError` is raised
        with the appropriate `errno`, unless the error is `EINTR`, which results
        in the call to be retried.
        '''

        c_off_in = \
            ctypes.byref(c_loff_t(off_in)) if off_in is not None else None
        c_off_out = \
            ctypes.byref(c_loff_t(off_out)) if off_out is not None else None

        # For handling EINTR...
        while True:
            res = c_splice(fd_in, c_off_in, fd_out, c_off_out, len_, flags)

            if res == -1:
                errno_ = ctypes.get_errno()

                # Try again on EINTR
                if errno_ == errno.EINTR:
                    continue

                raise IOError(errno_, os.strerror(errno_))

            return res

    return splice

# Build and export wrapper
splice = make_splice()  # pylint: disable-msg=C0103
del make_splice


# From bits/fcntl.h
# Values for 'flags', can be OR'ed together
SPLICE_F_MOVE = 1
SPLICE_F_NONBLOCK = 2
SPLICE_F_MORE = 4
SPLICE_F_GIFT = 8


def main(host, port, path):
    '''Server implementation'''

    # Set up a simple server socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(1)

    # Single accept, we'll clean up once this one connection has been handled.
    # Yes, this is a very stupid server indeed.
    conn, addr = sock.accept()
    print 'Connection from:', addr

    # Set up some subprocess which produces some output which should be
    # transferred to the client.
    # In this case, we just 'cat' this source file.
    argv = ['cat', path]
    # Might want to do something about stdin and stdout as well in a serious
    # application
    proc = subprocess.Popen(argv, close_fds=True, stdout=subprocess.PIPE)

    # We need the integer FDs for splice to work
    pipe_fd = proc.stdout.fileno()
    conn_fd = conn.fileno() #pylint: disable-msg=E1101
    print 'Will splice data from FD', pipe_fd, 'to', conn_fd

    transferred = 0

    # 32MB chunks
    chunksize = 32 * 1024 * 1024

    # If you know the number of bytes to be transferred upfront, you could
    # change this into a 'while todo > 0', pass 'todo' to splice instead of the
    # arbitrary 'chunksize', and error out if splice returns 0 before all bytes
    # are transferred.
    # In this example, we just transfer as much as possible until the write-end
    # closes the pipe.
    while True:
        done = splice(pipe_fd, None, conn_fd, None, chunksize,
                        SPLICE_F_MOVE | SPLICE_F_MORE)

        if done == 0:
            # Write-end of the source pipe has gone, no more data will be
            # available
            break

        transferred += done

    print 'Bytes transferred:', transferred

    # Close client and server socket
    conn.close()
    sock.close()

    # Wait for subprocess to finish (it should be finished by now anyway...)
    proc.wait()


if __name__ == '__main__':
    main('', 9009, os.path.abspath(__file__))
