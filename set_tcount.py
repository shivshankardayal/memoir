from couchbase.bucket import Bucket

mb = Bucket("couchbase:///memoir")

# just mention tags count in case deletion is manual
mb.set('tcount', 107)
