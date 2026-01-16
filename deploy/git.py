from deploy.config import DeployConfig
from deploy.git_over_cdn.client import GitOverCdnClient
from deploy.logger import logger
from deploy.utils import *

import argparse
import subprocess
import sys


class GitManager(DeployConfig):
    @cached_property
    def git(self):
        exe = self.filepath('GitExecutable')
        if os.path.exists(exe):
            return exe

        logger.warning(f'GitExecutable: {exe} does not exist, use `git` instead')
        return 'git'

    @staticmethod
    def remove(file):
        try:
            os.remove(file)
            logger.info(f'Removed file: {file}')
        except FileNotFoundError:
            logger.info(f'File not found: {file}')

    def git_repository_init(
            self, repo, source='origin', branch='master', proxy='', ssl_verify=True
    ):
        logger.hr('Git Init', 1)
        if not self.execute(f'"{self.git}" init', allow_failure=True):
            self.remove('./.git/config')
            self.remove('./.git/index')
            self.remove('./.git/HEAD')
            self.execute(f'"{self.git}" init')

        logger.hr('Set Git Proxy', 1)
        if proxy:
            self.execute(f'"{self.git}" config --local http.proxy {proxy}')
            self.execute(f'"{self.git}" config --local https.proxy {proxy}')
        else:
            self.execute(f'"{self.git}" config --local --unset http.proxy', allow_failure=True)
            self.execute(f'"{self.git}" config --local --unset https.proxy', allow_failure=True)

        if ssl_verify:
            self.execute(f'"{self.git}" config --local http.sslVerify true', allow_failure=True)
        else:
            self.execute(f'"{self.git}" config --local http.sslVerify false', allow_failure=True)

        logger.hr('Set Git Repository', 1)
        if not self.execute(f'"{self.git}" remote set-url {source} {repo}', allow_failure=True):
            self.execute(f'"{self.git}" remote add {source} {repo}')

        logger.hr('Fetch Repository Branch', 1)
        self.execute(f'"{self.git}" fetch {source} {branch}')

        logger.hr('Pull Repository Branch', 1)
        # Remove git lock
        for lock_file in [
            './.git/index.lock',
            './.git/HEAD.lock',
            './.git/refs/heads/master.lock',
        ]:
            if os.path.exists(lock_file):
                logger.info(f'Lock file {lock_file} exists, removing')
                os.remove(lock_file)
        self.execute(f'"{self.git}" reset --hard {source}/{branch}')
        self.execute(f'"{self.git}" pull --ff-only {source} {branch}')

        logger.hr('Show Version', 1)
        self.execute(f'"{self.git}" --no-pager log --no-merges -1')

    @property
    def goc_client(self):
        client = GitOverCdnClient(
            url='https://vip.123pan.cn/1818706573/pack/LmeSzinc_AzurLaneAutoScript_master',
            folder=self.root_filepath,
            source='origin',
            branch='master',
            git=self.git,
        )
        client.logger = logger
        return client

    def git_install(self):
        logger.hr('Update Alas', 0)

        if not self.AutoUpdate:
            logger.info('AutoUpdate is disabled, skip')
            return

        if self.GitOverCdn:
            if self.goc_client.update():
                return

        self.git_repository_init(
            repo=self.Repository,
            source='origin',
            branch=self.Branch,
            proxy=self.GitProxy,
            ssl_verify=self.SSLVerify,
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=True)
    sub = parser.add_subparsers(dest="cmd")

    fetch_upstream = sub.add_parser("fetch-upstream")
    fetch_upstream.add_argument("--remote", default="upstream")
    fetch_upstream.add_argument("--url", required=True)
    fetch_upstream.add_argument("--branch", default="master")

    sync_upstream = sub.add_parser("sync-upstream")
    sync_upstream.add_argument("--remote", default="upstream")
    sync_upstream.add_argument("--url")
    sync_upstream.add_argument("--branch", default="master")
    sync_upstream.add_argument("--strategy", choices=["rebase", "merge", "ff-only"], default="rebase")

    args, unknown = parser.parse_known_args()

    self = GitManager()

    git_exe = self.git

    def run_git(*argv):
        return subprocess.check_call([git_exe, *argv], stdout=sys.stdout, stderr=sys.stderr)

    if args.cmd == "fetch-upstream":
        remote = args.remote
        url = args.url
        branch = args.branch

        try:
            run_git("remote", "set-url", remote, url)
        except Exception:
            run_git("remote", "add", remote, url)

        run_git("fetch", remote, branch)
        run_git("--no-pager", "log", "--no-merges", "-1", "--oneline", f"{remote}/{branch}")
        sys.exit(0)

    if args.cmd == "sync-upstream":
        remote = args.remote
        url = args.url
        branch = args.branch
        strategy = args.strategy

        if url:
            try:
                run_git("remote", "set-url", remote, url)
            except Exception:
                run_git("remote", "add", remote, url)

        run_git("fetch", remote, branch)
        if strategy == "rebase":
            run_git("rebase", f"{remote}/{branch}")
        elif strategy == "merge":
            run_git("merge", f"{remote}/{branch}")
        else:
            run_git("merge", "--ff-only", f"{remote}/{branch}")
        run_git("--no-pager", "log", "--no-merges", "-1", "--oneline")
        sys.exit(0)

    self.goc_client.get_status()
