from typing import Literal
import heapq

class RandomNumberLimitExceeded(Exception):
    """Raised when random number generator reaches its limit"""
    pass

type EventType = Literal["arrival", "departure", "passage"]
class Event:
    def __init__(self, time: float, type: EventType, queue_index: int):
        self.time = time
        self.type = type
        self.queue_index = queue_index

class RandomNumberGenerator:
    _instance = None
    
    def __new__(cls, a=25214903917, c=11, M=2**48, seed=1, count=100):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.a = a
            cls._instance.c = c
            cls._instance.M = M
            cls._instance.seed = seed
            cls._instance.count = count
            cls._instance.generated = 0
        return cls._instance

    def next(self):
        if self.generated >= self.count:
            raise RandomNumberLimitExceeded(f"Random number limit ({self.count}) reached")
        self.seed = (self.a * self.seed + self.c) % self.M
        self.generated += 1
        return self.normalize(self.seed)
    
    def normalize(self, value):
        return value / self.M
    
    def reset(self):
        self.generated = 0
    
type IntervalGenerator = tuple[float, float]

class QueueSimulator:
    def __init__(self, queues: list[Queue], count = 100, first_arrival_time: float = 2.0):
        self.random_count = count
        self.first_arrival_time = first_arrival_time
        self.queues = queues
        self.scheduler = Scheduler(first_arrival_time=self.first_arrival_time, random_count=count)
        self.initialize_queues()

    def initialize_queues(self):
        for i, queue in enumerate(self.queues):
            queue.set_index(i)

    def run(self):
        try:
            while True:
                event = self.scheduler.next()
                if event is None:
                    break
                self.accumulate_time(event.time)
                if event.type == "arrival":
                    self.queues[event.queue_index].arrival(self.scheduler)
                elif event.type == "departure":
                    self.queues[event.queue_index].departure(self.scheduler)
                elif event.type == "passage":
                    self.queues[event.queue_index].passage_pass(self.scheduler)
                    # Routing to next queue
                    next_queue_index = self.scheduler.get_next_queue(event.queue_index)
                    if next_queue_index is not None and next_queue_index < len(self.queues):
                        is_last_queue = (next_queue_index == len(self.queues) - 1)
                        self.queues[next_queue_index].passage_receive(self.scheduler, is_last_queue)
        except RandomNumberLimitExceeded:
            pass
        finally:
            self.print_results()

    def accumulate_time(self, time: float):
        for queue in self.queues:
            queue.accumulate_time(time)

    def print_results(self):
        print()
        for queue in self.queues:
            queue.print_results()
            print()
        
        # General summary
        total_time = max([q.current_time for q in self.queues]) if self.queues else 0
        total_losses = sum([q.losses for q in self.queues])
        print(f"Total simulation time: {total_time}")
        print(f"Total lost customers: {total_losses}")
        print(f"Random numbers used: {self.scheduler.random_generator.generated}")

class Queue:
    def __init__(self, name: str, B: IntervalGenerator, C: int, K: int = int(10e10), A: IntervalGenerator = None):
        self.name = name
        self.servers = C
        self.capacity = K
        self.arrival_interval = A  # Only for source queue
        self.departure_interval = B
        self.initialize_structure()

    def initialize_structure(self):
        self.customers = 0
        self.current_time = 0
        self.times = []
        self.losses = 0
        
    def set_index(self, index: int):
        self.index = index

    def arrival(self, scheduler: Scheduler):
        if self.arrival_interval is None:
            return  # No external arrivals for intermediate queues
        if self.customers < self.capacity:
            self.customers += 1
            if self.customers <= self.servers:
                scheduler.add_passage(self.current_time, self.departure_interval, self.index)
        else:
            self.losses += 1
        scheduler.add_arrival(self.current_time, self.arrival_interval, self.index)

    def arrival(self, scheduler: Scheduler):
        if self.customers < self.capacity:
            self.customers += 1
            if self.customers <= self.servers:
                scheduler.add_passage(self.current_time, self.departure_interval, self.index)
        else:
            self.losses += 1
        scheduler.add_arrival(self.current_time, self.arrival_interval, self.index)

    def departure(self, scheduler: Scheduler):
        if self.customers > 0:
            self.customers -= 1
            if self.customers >= self.servers:
                scheduler.add_departure(self.current_time, self.departure_interval, self.index)

    def passage_receive(self, scheduler: Scheduler, is_last_queue: bool):
        if self.customers < self.capacity:
            self.customers += 1
            if self.customers <= self.servers:
                scheduler.add_departure(self.current_time, self.departure_interval, self.index) if is_last_queue else scheduler.add_passage(self.current_time, self.departure_interval, self.index)
        else:
            self.losses += 1

    def passage_pass(self, scheduler: Scheduler):
        if self.customers > 0:
            self.customers -= 1
            if self.customers >= self.servers:
                scheduler.add_passage(self.current_time, self.departure_interval, self.index)

    def accumulate_time(self, time: float):
        calculated_time = (time - self.current_time)
        if len(self.times) <= self.customers:
            self.times.append(calculated_time)
        else:
            self.times[self.customers] += calculated_time
        self.current_time = time

    def print_results(self):
        print(f"=== Results (Queue {self.index+1}) ===")
        print(f"Losses: {self.losses}")
        print(f"Total time: {self.current_time}")
        for i in range(len(self.times)):
            percentage = (self.times[i] * 100 / self.current_time) if self.current_time > 0 else 0
            print(f"{i}: {self.times[i]} ({percentage:.4f}%)")

class Scheduler:
    def __init__(self, first_arrival_time: float = 2.0, random_count: int = 100):
        self.events = []
        self.random_generator = RandomNumberGenerator(count=random_count)
        self.routing_map = {}  # Maps (source_queue_index, rnd_number) to target_queue_index
        heapq.heappush(self.events, (first_arrival_time, Event(first_arrival_time, "arrival", 0)))
    
    def set_routing(self, routing_map):
        """Set the routing map for passage events"""
        self.routing_map = routing_map

    def add_arrival(self, time: float, A: IntervalGenerator, queue_index: int):
        event_time = time + self.generate_event_time(A)
        event = Event(event_time, "arrival", queue_index)
        heapq.heappush(self.events, (event.time, event))

    def add_departure(self, time: float, B: IntervalGenerator, queue_index: int):
        event_time = time + self.generate_event_time(B)
        event = Event(event_time, "departure", queue_index)
        heapq.heappush(self.events, (event.time, event))

    def add_passage(self, time: float, B: IntervalGenerator, queue_index: int):
        event_time = time + self.generate_event_time(B)
        event = Event(event_time, "passage", queue_index)
        heapq.heappush(self.events, (event.time, event))

    def get_next_queue(self, current_queue_index: int):
        """Determine next queue based on routing probabilities"""
        if current_queue_index in self.routing_map:
            rnd = self.random_generator.next()
            cumulative = 0
            for prob, target_idx in self.routing_map[current_queue_index]:
                cumulative += prob
                if rnd <= cumulative:
                    return target_idx
            return self.routing_map[current_queue_index][-1][1]  # Default to last
        return None

    def next(self) -> Event | None:
        if not self.events:
            return None
        _, event = heapq.heappop(self.events)
        return event
    
    def generate_event_time(self, interval: IntervalGenerator):
        return (self.random_generator.next() * (interval[1] - interval[0])) + interval[0]

def main():
    # Queue 1: G/G/1 - 1 server, time 1..2min, arrival interval
    queue_1 = Queue(name="G/G/1", B=(1.0, 2.0), C=1, K=10000, A=(1.0, 2.0))
    
    # Queue 2: G/G/2/5 - 2 servers, capacity 5, time 4..6min
    queue_2 = Queue(name="G/G/2/5", B=(4.0, 6.0), C=2, K=5)
    
    # Queue 3: G/G/2/10 - 2 servers, capacity 10, time 5..15min
    queue_3 = Queue(name="G/G/2/10", B=(5.0, 15.0), C=2, K=10)
    
    queues = [queue_1, queue_2, queue_3]
    
    # Configure simulation
    count = 100_000  # 100,000 random numbers
    first_arrival_time = 2.4  # First customer at 2.4min
    simulator = QueueSimulator(queues=queues, count=count, first_arrival_time=first_arrival_time)
    
    # Configure probabilistic routing
    # Queue 0 (QUEUE1): 80% -> Queue 1 (QUEUE2), 20% -> Queue 2 (QUEUE3)
    # Queue 1 (QUEUE2): 100% -> EXIT
    # Queue 2 (QUEUE3): 100% -> EXIT
    routing_map = {
        0: [(0.8, 1), (0.2, 2)],  # From QUEUE1: 80% to QUEUE2, 20% to QUEUE3
        # QUEUEs 2 and 3 exit the system (EXIT)
    }
    simulator.scheduler.set_routing(routing_map)
    
    simulator.run()

def generate_10_random_numbers():
    rng = RandomNumberGenerator()
    for _ in range(10):
        print(rng.next())

if __name__ == "__main__":
    main()
    # generate_10_random_numbers()
