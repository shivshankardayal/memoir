from couchbase.bucket import Bucket
import sys

mb = Bucket("couchbase:///memoir")

print mb.get(sys.argv[1]).value
mb.delete(sys.argv[1])
mb.decr('tcount')
