from typing import List, Tuple


bucket_name: str = 'my-very-public-bucket'


# policy sets the appropriate bucket as world readable (no write)
# See the following good summary of Bucket Policies
# https://gist.github.com/krishnasrinivas/2f5a9affe6be6aff42fe723f02c86d6a
policy = {"Version": "2012-10-17",
          "Statement": [
              {
                  "Sid": "",
                  "Effect": "Allow",
                  "Principal": {"AWS": "*"},
                  "Action": "s3:GetBucketLocation",
                  "Resource": f"arn:aws:s3:::{bucket_name}"
              },
              {
                  "Sid": "",
                  "Effect": "Allow",
                  "Principal": {"AWS": "*"},
                  "Action": "s3:ListBucket",
                  "Resource": f"arn:aws:s3:::{bucket_name}"
              },
              {
                  "Sid": "",
                  "Effect": "Allow",
                  "Principal": {"AWS": "*"},
                  "Action": "s3:GetObject",
                  "Resource": f"arn:aws:s3:::{bucket_name}/*"
              }
          ]}

MINIO_POLICY_HOOKS: List[Tuple[str, dict]] = [  # This array of (bucket_name, policy) tuples belong to Django settings
    (bucket_name, policy),
]
