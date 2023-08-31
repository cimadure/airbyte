#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#
from concurrent.futures import Future
from queue import Queue
from typing import List, Optional

from airbyte_cdk.models import SyncMode
from airbyte_cdk.sources.stream_reader.concurrent.stream_partition import StreamPartition
from airbyte_cdk.sources.streams import Stream


class PartitionGenerator:
    def __init__(self, queue: Queue[Optional[StreamPartition]], name: str):
        self._queue = queue
        self._name = name
        self._futures: List[Future] = []

    def generate_partitions_for_stream(self, stream: Stream, sync_mode: SyncMode, cursor_field: Optional[List[str]]) -> None:
        print(f"generate_partitions_for_stream for {self._name} for stream {stream.name}")
        for partition in stream.generate_partitions(sync_mode=sync_mode, cursor_field=cursor_field):
            print(f"putting partition and stream on queue for {partition}. stream: {stream.name}")
            stream_partition = StreamPartition(stream, partition, cursor_field)
            self._queue.put(stream_partition)
        print(f"done. queue size: {self._queue.qsize()}")

    def generate_partitions_async(self, stream: Stream, sync_mode: SyncMode, cursor_field: Optional[List[str]], executor):
        f = executor.submit(
            PartitionGenerator.generate_partitions_for_stream,
            self,
            stream,
            sync_mode,
            cursor_field,
        )
        self._futures.append(f)

    def get_next_partition(self) -> Optional[StreamPartition]:
        if self._queue.qsize() > 0:
            return self._queue.get()
        else:
            return None

    def there_are_partitions_ready(self) -> bool:
        return self._queue.qsize() > 0

    def is_done(self) -> bool:
        return self._queue.qsize() == 0 and self._futures_are_done(self._futures)

    def _futures_are_done(self, futures):
        return all(future.done() for future in futures)

    def get_exceptions(self):
        return [future.exception() for future in self._futures if future.exception() is not None]
