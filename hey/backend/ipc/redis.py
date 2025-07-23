import time
import redis
import pickle
import socket

redis_pool = redis.ConnectionPool(
    host='127.0.0.1',
    port='6379',
    db=0,
    socket_keepalive=True,
    socket_keepalive_options={
        socket.TCP_KEEPCNT: 2,
        socket.TCP_KEEPINTVL: 30
    }
)
r = redis.Redis(connection_pool=redis_pool)


class RedisIPC(object):
    GET_WAITING_TIME_IN_SEC = 0.5

    def __init__(self, root):
        self.root = root

    @staticmethod
    def _list_to_key(key_list):
        key_list = [str(e) for e in key_list]
        key = "/" + "/".join(key_list)
        return key

    def _set_a_value(self, key, value):
        if isinstance(key, list):
            key = self._list_to_key(key_list=key)
        key = f"{self.root}/{key}"
        r.set(name=key, value=pickle.dumps(value))

    def set_a_shared_value(self, key, value):
        self._set_a_value(key=key, value=value)

    def _get_a_value(self, key, busy_waiting=False):
        if isinstance(key, list):
            key = self._list_to_key(key_list=key)
        key = f"{self.root}/{key}"

        raw_value = r.get(key)
        if raw_value is None:
            if busy_waiting:
                while not raw_value:
                    time.sleep(self.GET_WAITING_TIME_IN_SEC)
                    raw_value = r.get(key)
                return pickle.loads(raw_value)
            else:
                return None
        else:
            return pickle.loads(raw_value)

    def get_a_shared_value(self, key, busy_waiting=False):
        return self._get_a_value(key=key, busy_waiting=busy_waiting)

    def _delete_a_key(self, key):
        if isinstance(key, list):
            key = self._list_to_key(key_list=key)
        key = f"{self.root}/{key}"
        r.delete(key)

    def delete_a_shared_value(self, key):
        self._delete_a_key(key=key)

    def _keys_of_a_prefix(self, prefix):
        if isinstance(prefix, list):
            prefix = self._list_to_key(key_list=prefix)
        if len(prefix) == 0:
            prefix = "*"
        else:
            prefix = f"{prefix}/*"
        prefix = f"{self.root}/{prefix}"

        # Note that scanning can be too slow!
        # So do not abuse this function.
        l = [e.decode() for e in r.scan_iter(prefix)]
        return l

    def delete_all_keys(self):
        for key in self._keys_of_a_prefix(prefix=""):
            self._delete_a_key(key=key)

    def subscribe_channels(self, channels):
        sub = r.pubsub()
        sub.subscribe(*channels)
        return sub

    def publish_a_value(self, channel, value):
        r.publish(
            channel=channel,
            message=pickle.dumps(value)
        )
