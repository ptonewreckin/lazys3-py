import sys
import requests
from time import sleep
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

class S3:
    def __init__(self, bucket):
        self.bucket = bucket
        self.domain = f"http://{bucket}.s3.amazonaws.com"

    def exists(self):
        return self.code() != 404

    def code(self):
        try:
            response = requests.get(self.domain, timeout=5)
            return response.status_code
        except requests.exceptions.RequestException:
            return None


class Scanner:
    def __init__(self, wordlist):
        self.wordlist = wordlist

    def scan_bucket(self, word):
        bucket = S3(word)
        if bucket.exists():
            print(f"Found bucket: {bucket.bucket} ({bucket.code()})")

    def scan(self):
        with ThreadPoolExecutor() as executor:
            executor.map(self.scan_bucket, self.wordlist)


class Wordlist:
    ENVIRONMENTS = ["dev", "development", "stage", "s3", "staging", "prod", "production", "test"]
    PERMUTATIONS = ["permutation_raw", "permutation_envs", "permutation_host"]

    @classmethod
    def generate(cls, common_prefix, prefix_wordlist):
        wordlist = []
        for permutation in cls.PERMUTATIONS:
            wordlist.extend(getattr(cls, permutation)(common_prefix, prefix_wordlist))
        return list(set(wordlist))

    @classmethod
    def from_file(cls, prefix, file):
        with open(file) as f:
            prefix_wordlist = f.read().splitlines()
        return cls.generate(prefix, prefix_wordlist)

    @staticmethod
    def permutation_raw(common_prefix, _prefix_wordlist):
        return [common_prefix]

    @classmethod
    def permutation_envs(cls, common_prefix, prefix_wordlist):
        permutations = []
        for word in prefix_wordlist:
            for environment in cls.ENVIRONMENTS:
                for bucket_format in ['%s-%s-%s', '%s-%s.%s', '%s-%s%s', '%s.%s-%s', '%s.%s.%s']:
                    permutations.append(bucket_format % (common_prefix, word, environment))
        return permutations

    @classmethod
    def permutation_host(cls, common_prefix, prefix_wordlist):
        permutations = []
        for word in prefix_wordlist:
            for bucket_format in ['%s.%s', '%s-%s', '%s%s']:
                permutations.append(bucket_format % (common_prefix, word))
                permutations.append(bucket_format % (word, common_prefix))
        return permutations


if len(sys.argv) < 2:
    print("Usage: python lazys3-py.py <common_prefix>")
    sys.exit(1)

common_prefix = sys.argv[1]
wordlist_file = "common_bucket_prefixes.txt"

wordlist = Wordlist.from_file(common_prefix, wordlist_file)
print(f"Generated wordlist from file, {len(wordlist)} items...")

scanner = Scanner(wordlist)
scanner.scan()

