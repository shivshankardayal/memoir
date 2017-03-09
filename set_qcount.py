from couchbase.bucket import Bucket

mb = Bucket("couchbase:///memoir")

# just mention questions count in case deletion is manual
mb.set('qcount', 347)
