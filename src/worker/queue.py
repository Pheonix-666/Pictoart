import concurrent.futures
from src.config import settings
from src.worker.jobs import process_doctor_art_job

# ThreadPoolExecutor for lightweight local background processing
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def enqueue_art_generation_job(doctor_id: int):
    """
    Enqueues a doctor art generation task. Uses Redis Queue if WORKER_MODE == 'rq',
    otherwise uses background ThreadPoolExecutor.
    """
    if settings.WORKER_MODE.lower() == "rq":
        try:
            from redis import Redis
            from rq import Queue
            redis_conn = Redis.from_url(settings.REDIS_URL)
            q = Queue("art_jobs", connection=redis_conn)
            q.enqueue(process_doctor_art_job, doctor_id)
            print(f"[Queue] Job for Doctor #{doctor_id} enqueued into Redis Queue.")
            return
        except Exception as e:
            print(f"[Queue] Redis Queue connection failed ({str(e)}), falling back to ThreadPoolExecutor.")

    # Fallback / Local mode
    _executor.submit(process_doctor_art_job, doctor_id)
    print(f"[Queue] Job for Doctor #{doctor_id} submitted to ThreadPoolExecutor.")
