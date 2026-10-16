"""Calls to a local Ollama server, shared by the LLM-guided algorithms."""
import time

import requests

DEFAULT_PORT = 11434
# seconds to wait before each new attempt after a failed request (about 7.5 minutes in all)
RETRY_WAITS = (10, 30, 60, 120, 240)
# (connect, read) timeouts. The read timeout includes the time a request waits in the
# server's queue, which with many runs per server can exceed the generation itself.
TIMEOUT = (30, 3 * 3600)


def ollama_url(host):
    """'IP' or 'IP:PORT' (llm_ip in the scenario) -> URL of the generate endpoint."""
    if ':' not in host:
        host = f'{host}:{DEFAULT_PORT}'
    return f'http://{host}/api/generate'


def ollama_generate(host, model, prompt, num_ctx=32768, logger=None, waits=RETRY_WAITS):
    """
    Returns the model's response to prompt. A failed request (connection refused or
    reset, timeout, HTTP error) is retried after each of the waits; when all attempts
    fail, RuntimeError is raised, so that the run stops instead of silently carrying
    on without the LLM.
    """
    payload = {'model': model, 'prompt': prompt, 'stream': False, 'options': {'num_ctx': num_ctx}}
    url = ollama_url(host)
    last_error = None
    for attempt, wait in enumerate((0,) + tuple(waits)):
        if wait:
            if logger:
                logger.warning(f'Ollama request failed ({last_error}); retry {attempt}/{len(waits)} in {wait} s')
            time.sleep(wait)
        start = time.perf_counter()
        try:
            response = requests.post(url, json=payload, timeout=TIMEOUT)
            response.raise_for_status()
            text = response.json()['response']
        except (requests.RequestException, KeyError, ValueError) as error:
            last_error = error
            continue
        if logger:
            # wall-clock time of the call (queue + generation), outside any fitness measurement
            logger.info(f'[llm] Ollama call ({model}): {time.perf_counter() - start:.1f} s')
        return text
    raise RuntimeError(f'Ollama at {url} unavailable after {len(waits) + 1} attempts: {last_error}')
