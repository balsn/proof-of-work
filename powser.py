#!/usr/bin/env python3
import sqlite3
from time import time
import hashlib
import secrets
'''
db_path: required, where to save the sqlite3 database
difficulty: how many leading zero bits
clean_expired_rows_per: clean expire rows after n inserts
prefix_length: the length of prefix
default_expired_time: how long can a challenger solve the challenge in seconds, default is 10 minutes
min_refresh_time: how long can a challenger get a new challenge, default is half of default_expired_time
'''
class Powser:
    def __init__(
            self,
            db_path,
            difficulty=22,
            clean_expired_rows_per=1000,
            prefix_length=16,
            default_expired_time=None,
            min_refresh_time=None
        ):
        self.db = sqlite3.connect(db_path)
        self.difficulty = difficulty
        self.clean_expired_rows_per = clean_expired_rows_per
        self.prefix_length = prefix_length
        self.default_expired_time = max(600, 2**(difficulty-16)) if default_expired_time is None else default_expired_time
        self.min_refresh_time = self.default_expired_time // 2 if min_refresh_time is None else min_refresh_time

        self._insert_count = 0
        self._create_table()

    def get_challenge(self, ip):
        row = self.db.execute('SELECT prefix, valid_until FROM pow WHERE ip = ?', (ip, )).fetchone()
        if row is None:
            return self._update_row(ip)

        prefix, valid_until = row
        time_remain = valid_until - int(time())
        if time_remain <= self.min_refresh_time:
            return self._update_row(ip)
        return prefix, time_remain

    def verify_client(self, ip, answer, with_msg=False):
        row = self.db.execute('SELECT valid_until, prefix FROM pow WHERE ip=?', (ip, )).fetchone()
        if row is None:
            return (False, 'Please get a new PoW challenge.') if with_msg else False
        valid_until, prefix = row
        if int(time()) > valid_until:
            return (False, 'This PoW challenge is expired.') if with_msg else False
        result = self._verify_hash(prefix, answer)
        if not result:
            return (False, 'The answer is incorrect.') if with_msg else False
        self._update_row(ip)
        return (True, 'Okay.') if with_msg else True

    def clean_expired(self):
        self.db.execute('DELETE FROM pow WHERE valid_until < strftime("%s", "now")')
        self.db.commit()

    def close(self):
        self.db.close()

    def _verify_hash(self, prefix, answer):
        h = hashlib.sha256()
        h.update((prefix + answer).encode())
        bits = ''.join(bin(i)[2:].zfill(8) for i in h.digest())
        return bits.startswith('0' * self.difficulty)

    def _update_row(self, ip):
        self._insert_count += 1
        if self.clean_expired_rows_per > 0 and self._insert_count % self.clean_expired_rows_per == 0:
            self.clean_expired()
        prefix = secrets.token_urlsafe(self.prefix_length)[:self.prefix_length].replace('-', 'B').replace('_', 'A')
        now = int(time())
        valid_until = now + self.default_expired_time
        data = {
            'ip': ip,
            'valid_until': valid_until,
            'prefix': prefix
        }
        self.db.execute('INSERT OR REPLACE INTO pow VALUES(:ip, :valid_until, :prefix)', data)
        self.db.commit()
        return prefix, valid_until - now

    def _create_table(self):
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS pow (
                ip TEXT PRIMARY KEY,
                valid_until INTEGER,
                prefix TEXT
            )
        ''')
        self.db.commit()

if __name__ == '__main__':
    powser = Powser(db_path='./pow.sqlite3')
    ip = '240.240.240.240'
    prefix, time_remain = powser.get_challenge(ip)
    print(f'''
sha256({prefix} + ???) == {'0'*powser.difficulty}({powser.difficulty})...

IP: {ip}
Time remain: {time_remain} seconds
You need to await {time_remain - powser.min_refresh_time} seconds to get a new challenge.
''')
    last = int(time())
    i = 0
    while not powser._verify_hash(prefix, str(i)):
        i += 1
    print(int(time()) - last, 'seconds')
    print(f"sha256({prefix} + {i}) == {'0'*powser.difficulty}({powser.difficulty})")
    print(powser.verify_client(ip, str(i), with_msg=True))
    powser.close()
