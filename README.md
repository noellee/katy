# Katy - *Make CATe Great Again*

[![Build Status](https://travis-ci.org/noellee/katy.svg?branch=master)](https://travis-ci.org/noellee/katy)
[![Coverage Status](https://coveralls.io/repos/github/noellee/katy/badge.svg)](https://coveralls.io/github/noellee/katy)

I should be revising for exams but instead I made this ¯\\\_(ツ)\_/¯.
Can't possibly revise without a tool to help you download all notes, amirite?

## Command Line tools

Katy provides a suite (more like 2 now) command line tools to make your life
easier (only on CATe though - life is _hard_). It performs repetitive tasks for
you so you can be even more lazy you than already are!

For detailed instructions and information on how to use a specific script, do:

```
$ [script name].py --help
```

The following are some common use cases of the scripts.

#### Downloading all notes from a course

Copy the CATe url to the notes page of the module you want to download. It
should look something like
`https://cate.doc.ic.ac.uk/notes.cgi?key=[colon separated params]`. This url
will be needed to download notes using `cate_download.py`. In the examples
below, `[cate url]` refers to this url.

##### e.g. Downloading notes numbered 1-10

```
$ cate_download.py [cate url] 1-10
```
