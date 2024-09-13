export class SkynetClient {
    constructor(options = {}) {
        this._baseUrl = options.baseUrl ?? 'http://localhost:8000';
    }

    async summary(text, options) {
        return this._fetchAndPoll(`${this._baseUrl}/summaries/v1/summary`, text, options)
    }

    async actionItems(text, options) {
        return this._fetchAndPoll(`${this._baseUrl}/summaries/v1/action-items`, text, options)
    }

    async _fetchAndPoll(url, text, options = {}) {
        // Submit the job.
        const r = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                hint: options?.hint ?? 'text',
                text
            })
        });
        const data = await r.json();
        const jobId = data.id;

        if (!jobId) {
            throw new Error('Could not create job');
        }

        const d = createDeferred();

        // Poll for it.
        const int = setInterval(async () => {
            try {
                const r = await fetch(`${this._baseUrl}/summaries/v1/job/${jobId}`);
                const data = await r.json();
    
                if (data.status === 'success') {
                    clearInterval(int);
                    d.resolve(data.result);
                } else if (data.status === 'error') {
                    clearInterval(int);
                    d.reject(new Error(data.result));
                }
            } catch(_) {}
        }, 5 * 1000);

        return d.promise;
    }
}


function createDeferred() {
    if (Promise.withResolvers) {
        return Promise.withResolvers();
    }

    const d = {};

    d.promise = new Promise((resolve, reject) => {
        d.resolve = resolve;
        d.reject = reject;
    })

    return d;
}
