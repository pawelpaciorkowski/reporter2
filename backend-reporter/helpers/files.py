import glob
import random
import string
import subprocess
import tempfile
import os
import shutil
import zipfile

try:
    import pyminizip

    ZIP_PASSWORD_ENABLED = True
except ImportError:
    ZIP_PASSWORD_ENABLED = False


def copy_from_remote(adres, remote_path, local_path):
    cmd = ['scp', '%s:%s' % (adres, remote_path), local_path]
    proc = subprocess.Popen(cmd)
    res = proc.communicate()
    return proc.returncode == 0


def run_on_remote(adres, command, input=None):
    proc = subprocess.Popen(['ssh', adres, command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    stdout, stderr = proc.communicate(input=input)
    return stdout, stderr


def random_path(prefix=None, extension=None):
    fn = tempfile.gettempdir()
    while os.path.exists(fn):
        fn = ''.join(random.choice(string.ascii_letters) for i in range(12))
        if prefix is not None:
            fn = prefix + '_' + fn
        if extension is not None:
            fn = fn + '.' + extension
        fn = os.path.join(tempfile.gettempdir(), fn)
    return fn


class ZIP:
    def __init__(self):
        self.src_files = []
        self.dst_files = []
        self.file_is_temporary = []
        self.password = None

    def add_file(self, fn, dest_fn=None, remove_after_create=False):
        self.src_files.append(fn)
        if dest_fn is None:
            dest_fn = os.path.basename(fn)
        self.dst_files.append(dest_fn)
        self.file_is_temporary.append(remove_after_create)

    def add_file_from_bytes(self, fn, content):
        tmp_fn = random_path('zip_part')
        with open(tmp_fn, 'wb') as f:
            f.write(content)
        self.add_file(tmp_fn, fn, True)

    def set_password(self, password):
        if not ZIP_PASSWORD_ENABLED:
            raise NotImplementedError("ZIP passwords are not supported - install pyminizip")
        if isinstance(password, str):
            password = password.encode()
        self.password = password

    def _create_zip_zipfilie(self, fn):
        with zipfile.ZipFile(fn, 'w') as zf:
            for src_fn, dst_fn in zip(self.src_files, self.dst_files):
                zf.write(src_fn, dst_fn)

    def _copy_file(self, tmp_dir, src_fn, dst_fn):
        res = []
        dst_path = os.path.join(tmp_dir, dst_fn)
        if os.path.isdir(src_fn):
            os.makedirs(dst_path)
            for f in glob.glob(os.path.join(src_fn, '*')):
                bn = os.path.basename(f)
                res += self._copy_file(tmp_dir, f, os.path.join(dst_fn, bn))
        else:
            shutil.copy(src_fn, dst_path)
            res.append(dst_path)
        return res

    def _create_zip_pyminizip(self, fn):
        tmp_dir = random_path('zip_temp')
        src_files = []
        os.mkdir(tmp_dir, 0o700)
        for src_fn, dst_fn in zip(self.src_files, self.dst_files):
            src_files += self._copy_file(tmp_dir, src_fn, dst_fn)
        pyminizip.compress_multiple(src_files, [], fn, self.password, 0)
        shutil.rmtree(tmp_dir, True)

    def save_to_file(self, fn=None):
        if fn is None:
            fn = random_path(None, 'zip')
        if ZIP_PASSWORD_ENABLED:
            self._create_zip_pyminizip(fn)
        else:
            self._create_zip_zipfilie(fn)
        for src_fn, is_temporary in zip(self.src_files, self.file_is_temporary):
            if is_temporary:
                os.unlink(src_fn)
        return fn

    def save_as_bytes(self):
        fn = self.save_to_file()
        with open(fn, 'rb') as f:
            result = f.read()
        os.unlink(fn)
        return result
