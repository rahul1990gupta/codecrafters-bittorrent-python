import threading
import queue


class TestThreading:
    def __init__(self):

        self.q = queue.Queue()
        self.result = [None] * 30

    def worker(self):
        while True:
            item = self.q.get()
            print(f'Working on {item}')
            self.result[item] = item
            print(f'Finished {item}')
            self.q.task_done()

    def run(self):
        # Turn-on the worker thread.
        for i in range(5):
            threading.Thread(target=self.worker, daemon=True).start()

        # Send thirty task requests to the worker.
        for item in range(30):
            self.q.put(item)

        # Block until all tasks are done.
        self.q.join()
        print(self.result)

j = TestThreading()
j.run()

# from threading import Thread

# def hello():
#     print("Hello")

# threads = []

# for _ in range(10):
#     t = Thread(target=print, args=[1])
#     threads.append(t)


# t.run()
