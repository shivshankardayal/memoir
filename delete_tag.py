from couchbase.bucket import Bucket
import sys

mb = Bucket("couchbase:///memoir")

#:print mb.get(sys.argv[1]).value
mb.delete("{\"total_rows\":76,\"rows\":[\r\n]\r\n}\n")
mb.decr('tcount')
