# Description: This script is used to run skynet requests from a dump file
# Usage: poetry run python -m run-skynet-requests -f <skynet-jobs-dump-file> -m <max-requests> -s <sleep-time> -u <skynet-url>
# Prerequisites: skynet jobs dump file and a running skynet instance

import asyncio
import json
import aiohttp

from argparse import ArgumentParser
from tqdm import tqdm


parser = ArgumentParser()
parser.add_argument('-f', '--file', dest='filename', help='skynet jobs dump file ', metavar='FILE')
parser.add_argument('-m', '--max', dest='max_requests', help='max requests to make', default=10)
parser.add_argument('-s', '--sleep', dest='sleep', help='sleep time in seconds. Should be an estimate of how long max_requests needs to be processed', default=600)
parser.add_argument('-u', '--url', dest='url', help='skynet url', default='http://localhost:8000')
parser.add_argument('-jwt', '--jwt', dest='jwt', help='jwt token', default=None)
parser.add_argument('-t', '--type', dest='type', help='job type', default='any')

args = parser.parse_args()

jobs = open(args.filename, 'r').readlines()

if args.type != 'any':
    jobs = [job for job in jobs if json.loads(job)['type'] == args.type]

max_requests = int(args.max_requests)
base_url = args.url
jwt = args.jwt
sleep_time = int(args.sleep)


async def main():
    session = aiohttp.ClientSession(headers={'Authorization': f'Bearer {jwt}'} if jwt else {})

    async def post(job_type, data):
        path = 'summaries/v1/summary' if job_type == 'summary' else 'summaries/v1/action-items'
        url = f'{base_url}/{path}'

        async with session.post(url, json=data) as response:
            return await response.json()
        
    async def get(job_id):
        url = f'{base_url}/summaries/v1/job/{job_id}'

        async with session.get(url) as response:
            return await response.json()

    tasks = []
    ids = []

    # extract top max_requests from the dump file
    for i in range(min(max_requests, len(jobs))):
        job = json.loads(jobs[i])
        payload = {
            'text': job['payload']['text'],
        }

        tasks.append(post(job['type'], payload))

    # execute the requests and store the job ids
    try:
        responses = await asyncio.gather(*tasks)
        for response in responses:
            job_id = response['id']
            ids.append(job_id)
            print(f'Job ID: {job_id}')
    except Exception as e:
        print(e)

    # sleep for a while to allow the jobs to be processed (this replaces the need for polling)
    for _ in tqdm(range(sleep_time), desc='Waiting for jobs to be processed'):
        await asyncio.sleep(1)

    success = True
    total_duration = 0

    # get the results of the jobs
    for job_id in ids:
        response = await get(job_id)
        status = response['status']
        duration = response['duration']
        total_duration += duration

        print(f'Job {job_id} status: {status} duration: {duration} \n')

        if status != 'success':
            success = False

    print(f'Total duration: {total_duration}')

    await session.close()

    exit(1 if not success else 0)

asyncio.run(main())
