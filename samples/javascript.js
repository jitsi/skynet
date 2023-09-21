const jwt = ''

const getJob = async jobId => {
  const response = await fetch(`https://skynet-pilot.jitsi.net/summaries/v1/job/${jobId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${jwt}`
    }
  })

  return response.json()
}

const createJob = async text => {
  const response = await fetch('https://skynet-pilot.jitsi.net/summaries/v1/summary', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${jwt}`
    },
    body: JSON.stringify({
      text
    })
  })

  const { id } = await response.json()

  return id
}

const generateSummary = async text => {
  // submit a text to be summarized and get a job id in return
  const jobId = await createJob(text)

  /* eslint-disable-next-line no-async-promise-executor */
  const shortPoll = () => new Promise(async (resolve, reject) => {
    // retrieve job object according to schema specified at https://skynet-pilot.jitsi.net/summaries/v1/docs
    try {
      const job = await getJob(jobId)

      if (job.status === 'pending') {
        setTimeout(() => {
          shortPoll()
            .then(resolve)
            .catch(reject)
        }, 5000)
      } else {
        resolve(job)
      }
    } catch (e) {
      reject(new Error('Cannot retrieve job object'))
    }
  })

  // delay initial request
  setTimeout(async () => {
    try {
      const job = await shortPoll()

      if (job.status === 'success') {
        console.log(`summary: ${job.result}. Time to summarize: ${job.duration} sec`)
      } else if (job.status === 'error') {
        console.log(`failed to summarize text. Encountered an error: ${job.result}`)
      }
    } catch (e) {
      // handle exception
    }
  }, 5000)
}
