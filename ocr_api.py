import requests
import json
from time import sleep

# Limited to about 5 calls per day with 'TEST' key
url = "https://ocr.asprise.com/api/v1/receipt"

def get_results(image_path):
    def post():
        res = requests.post(url,
                            data = {
                                'api_key':'TEST',
                                'recognizer':'auto',
                                'ref_no':'ocr_python_xyz'
                            },
                            files = {
                                'file':open(image_path,'rb')
                            },
                            timeout=10) # will timeout after 10 seconds
        return res
    try:
        res = post()
    except requests.Timeout:
        print('Timeout. Will wait 10s and try again')
        sleep(10)
        res = post()
    except requests.ConnectionError:
        print('Could not connect!')
    if res.status_code==200:
        print(f"Status Code:{res.status_code}, success!!")
    else:
        print(f"Bad status code: {res.status_code}")
    return res

def write_json(jobj, filename):
    filename = filename.split('.')[0] # remove the extension
    with open(f'json/{filename}.json', 'w', encoding='utf-8') as f:
        json.dump(jobj, f, ensure_ascii=False, indent=4)
    
     
def main(img_path=None):
    if img_path == None:
        img_path = input('Enter the receipt pic filename:\n')
    res = get_results(img_path)
    jobj = json.loads(res.text)
    write_json(jobj, img_path)
    
if __name__ == "__main__":
    main()