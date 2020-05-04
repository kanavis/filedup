#!/usr/bin/env python

import argparse
import hashlib
import os
import sys
import time
from collections import defaultdict
from typing import List, Dict, Optional


class Progressbar:
    """ Progressbar """
    _prefix: str
    _pos: int
    _max: int
    _sym_len: int
    _cur_k: float
    _cur_n_sym: int
    _cur_per_mile: int

    def __init__(self, prefix: str, max_val: int, sym_len: int = 40):
        """ Constructor """
        self._pos = 0
        self._cur_n_sym = 0
        self._cur_per_mile = 0
        self._cur_k = 0.0
        self._prefix = prefix
        self._max = max_val
        self._sym_len = sym_len
        self._time_start = time.time()
        self.render()

    @staticmethod
    def _hr_eta(eta: int) -> str:
        """ Human readable ETA """
        parts: List[int] = []
        h_eta = int(eta/3600)
        if parts or h_eta:
            parts.append(h_eta)
        eta -= h_eta * 3600
        m_eta = int(eta/60)
        parts.append(m_eta)
        eta -= m_eta * 60
        parts.append(eta)
        return ':'.join(map(lambda x: '{:02d}'.format(x), parts))

    def render(self):
        """ Render """
        n_empty = self._sym_len - self._cur_n_sym
        percent = int(self._cur_per_mile / 10)
        if percent > 0:
            total_sec = time.time() - self._time_start
            eta_sec = int((1 - self._cur_k) * (total_sec / self._cur_k))
            eta = 'ETA: {}'.format(self._hr_eta(eta_sec))
        else:
            eta = ''
        prb = '[{}{}]'.format('*' * self._cur_n_sym, ' ' * n_empty)
        print(
            '\r{} {} {}% {}    '.format(self._prefix, prb, percent, eta),
            end='',
        )

    def add(self, pos: int):
        """ Add pos """
        self._pos += pos
        self._cur_k = self._pos/self._max
        n_sym = int(self._sym_len * self._cur_k)
        per_mile = int(self._cur_k*1000)
        if n_sym != self._cur_n_sym or per_mile != self._cur_per_mile:
            self._cur_n_sym = n_sym
            self._cur_per_mile = per_mile
            self.render()


class FileFilter:
    def check(self, path) -> bool:
        raise NotImplementedError()


class ExtensionFilter(FileFilter):
    def __init__(self, ext: str):
        self.ext = ext
        
    def check(self, path):
        return path.endswith('.{}'.format(self.ext))


class FileDup:
    """ Main app class """
    paths: List[str]
    files: List[str]
    total_size: int
    progress: bool
    progressbar: Optional[Progressbar] = None
    filters: List[FileFilter]

    files_by_size: Dict[int, List[str]]
    file_hashes: Dict[str, str]
    dup: Dict[str, List[str]]

    def _check_file_filters(self, file_path: str) -> bool:
        return not all(f.check(file_path) for f in self.filters)

    def _find_files_in_path(self, path):
        """ Process path """
        try:
            if os.path.isfile(path) or os.path.islink(path):
                self.total_size += os.stat(path).st_size
                if self._check_file_filters(path):
                    self.files.append(path)
            elif os.path.isdir(path):
                for sub_path in os.listdir(path):
                    self._find_files_in_path(os.path.join(path, sub_path))
        except OSError as err:
            print(err, file=sys.stderr)

    def __init__(
        self,
        paths: List[str],
        filters: List[FileFilter],
        progress: bool
    ):
        """ Constructor """
        self.files = []
        self.filters = filters
        self.paths = paths
        self.files_by_size = {}
        self.file_hashes = {}
        self.dup = {}
        self.progress = progress

    def _hash(self, file) -> str:
        """ Compute or return file hash """
        md5 = hashlib.md5()
        with open(file, 'rb') as f:
            for b in iter(lambda: f.read(4096), b''):
                if self.progressbar is not None:
                    self.progressbar.add(len(b))
                md5.update(b)

        return md5.hexdigest()

    def _process_file(self, file_path):
        """ Process file """


    def run(self, script: bool, print_hash: bool):
        """ App body """
        self.files_by_size = defaultdict(list)
        self.file_hashes = {}
        self.dup = defaultdict(list)

        # Compute
        for file in self.files:
            try:
                self._process_file(file)
            except OSError as err:
                print(err, file=sys.stderr)

        # Output
        if self.progressbar is not None:
            print()
        if script:
            # Script output
            for info, rec in self.dup.items():
                if print_hash:
                    print('{}|'.format('|'.join(info), end=''))
                print('|'.join(file for file in rec))
        else:
            # Human output
            if self.dup:
                print('Duplicate files:')
                for info, rec in self.dup.items():
                    if print_hash:
                        print('{}: '.format(info[0]), end='')
                    print(', '.join(file for file in rec))
            else:
                print('No duplicate files')


def path_arg(path):
    """ Path argument """
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError('Wrong path {}'.format(path))
    if (not os.path.isdir(path) and not os.path.islink(path)
            and not os.path.isfile(path)):
        raise argparse.ArgumentTypeError('Path {} is not dir, file or link'
                                         .format(path))
    return path


def main():
    """ Main """
    # Parse args
    parser = argparse.ArgumentParser(description='Find duplicate files')
    parser.add_argument('-s', '--script', action='store_true',
                        help='Simple to parse format')
    parser.add_argument('-P', '--progress', action='store_true',
                        help='Show progressbar')
    parser.add_argument('-H', '--print-hash', action='store_true',
                        help='Show file md5 hash')
    parser.add_argument('path', nargs='+', type=path_arg)

    args = parser.parse_args()

    # Parse filters
    filters = []

    # Run
    try:
        app = FileDup(paths=args.path, progress=args.progress, filters=filters)
        app.run(script=args.script, print_hash=args.print_hash)
    except KeyboardInterrupt:
        print('Interrupted')


main()
