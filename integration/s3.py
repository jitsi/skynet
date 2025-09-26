import os

async def run():
    from skynet.modules.ttt.s3 import S3

    s3 = S3()

    file = './test_upload.txt'
    # create a test file
    with open(file, 'w') as f:
        f.write('This is a test file for S3 integration.')

    # # # Test upload
    await s3.upload_file(file)

    # # delete the local test file
    os.remove(file)

    # # # Test download
    await s3.download_file(file)

    # # # Check if the file exists after download
    if not os.path.exists(file):
        raise Exception('Downloaded file does not exist')

    # # # Test delete
    await s3.delete_file(file)
    os.remove(file)

    # # # Check if the file is deleted from S3
    await s3.download_file(file)

    if os.path.exists(file):
        raise Exception('File was not deleted from S3')
