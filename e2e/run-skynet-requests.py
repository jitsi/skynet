# Description: This script is used to run skynet requests from a dump file
# Usage: poetry run python -m run-skynet-requests -f <skynet-jobs-dump-file> -m <max-requests> -s <sleep-time> -u <skynet-url>
# Prerequisites: skynet jobs dump file and a running skynet instance

import asyncio
import json
import os

from argparse import ArgumentParser
from pathlib import Path

import aiohttp
from tqdm import tqdm


parser = ArgumentParser()
parser.add_argument('-f', '--file', dest='filename', help='skynet jobs dump file ', metavar='FILE')
parser.add_argument('-F', '--folder', dest='folder', help='folder containing text files to summarize')
parser.add_argument('-o', '--output', dest='output', help='output folder')
parser.add_argument('-m', '--max', dest='max_requests', help='max requests to make', default=10)
parser.add_argument(
    '-s',
    '--sleep',
    dest='sleep',
    help='sleep time in seconds. Should be an estimate of how long max_requests needs to be processed',
    default=600,
)
parser.add_argument('-u', '--url', dest='url', help='skynet url', default='http://localhost:8000')
parser.add_argument('-jwt', '--jwt', dest='jwt', help='jwt token', default=None)
parser.add_argument('-t', '--type', dest='type', help='job type', default='any')

args = parser.parse_args()

max_requests = int(args.max_requests)
base_url = args.url
jwt = args.jwt
sleep_time = int(args.sleep)
jobs = []
ids = []
id_filename_map = {}

session = None

if args.filename:
    jobs = open(args.filename, 'r').readlines()

    if args.type != 'any':
        jobs = [json.loads(job) for job in jobs if json.loads(job)['type'] == args.type]
elif args.folder:
    text_files = [f for f in Path(args.folder).rglob('*.txt')]
    for file in text_files[:max_requests]:
        with open(file, 'r') as f:
            text = f.read()

            jobs.append({'type': 'summary', 'payload': {'text': text}, 'filename': file.name})


async def post(job_type, data, filename):
    path = 'summaries/v1/summary' if job_type == 'summary' else 'summaries/v1/action-items'
    url = f'{base_url}/{path}'

    async with session.post(url, json=data) as response:
        return await response.json(), filename


async def get(job_id):
    url = f'{base_url}/summaries/v1/job/{job_id}'

    async with session.get(url) as response:
        return await response.json()


async def main():
    global session
    session = aiohttp.ClientSession(headers={'Authorization': f'Bearer {jwt}'} if jwt else {})
    tasks = []

    # extract top max_requests from the dump file
    for i in range(min(max_requests, len(jobs))):
        job = jobs[i]
        payload = {
            'text': job['payload']['text'],
        }

        tasks.append(post(job['type'], payload, job['filename']))

    # execute the requests and store the job ids
    try:
        responses = await asyncio.gather(*tasks)
        for response, filename in responses:
            job_id = response['id']
            ids.append(job_id)
            id_filename_map[job_id] = filename
            print(f'Job ID: {job_id}')
    except Exception as e:
        print(e)

    # sleep for a while to allow the jobs to be processed (this replaces the need for polling)
    for _ in tqdm(range(sleep_time), desc='Waiting for jobs to be processed'):
        await asyncio.sleep(1)

    await get_results()


async def get_results():
    try:
        if args.filename:
            total_duration = 0

            for job_id in ids:
                response = await get(job_id)
                status = response['status']
                duration = response['duration']
                total_duration += duration

                print(f'Job {job_id} status: {status} duration: {duration} \n {response["result"]} \n')

                if status != 'success':
                    pass

            print(f'Total duration: {total_duration}')

        if args.output:
            os.makedirs(args.output, exist_ok=True)

            for job_id, filename in id_filename_map.items():
                response = await get(job_id)
                result = response['result']
                status = response['status']

                if not result:
                    raise Exception('Job is still running')

                with open(f'{args.output}/{filename}', 'w') as f:
                    f.write(result)
    except Exception as e:
        print(e)

        for _ in tqdm(range(max(1, int(sleep_time / 10))), desc='Waiting a bit more'):
            await asyncio.sleep(1)

        await get_results()

    await session.close()


asyncio.run(main())
