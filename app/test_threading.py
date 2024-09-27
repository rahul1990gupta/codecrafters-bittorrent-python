import threading
import queue

# q = queue.Queue()
# result = [None] * 30
# def worker():
#     while True:
#         item = q.get()
#         print(f'Working on {item}')
#         if item > 15:
#             result[item] = item

#         print(f'Finished {item}')
#         q.task_done()

# # Turn-on the worker thread.
# for i in range(5):
#     threading.Thread(target=worker, daemon=True).start()

# # Send thirty task requests to the worker.
# for item in range(30):
#     q.put(item)

# # Block until all tasks are done.
# q.join()
# print(result)


from threading import Thread

def hello():
    print("Hello")

threads = []

for _ in range(10):
    t = Thread(target=print, args=[1])
    threads.append(t)


t.run()
