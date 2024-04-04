import json
import os.path
import tempfile
import urllib.parse

import IPython.display
import pandas
import requests

API_BASE = "https://felt.com/api/v1/"
MAPS_URL = urllib.parse.urljoin(API_BASE, "maps")
LAYERS_TPL = urllib.parse.urljoin(API_BASE, "maps/{map_id}/layers")
FINISH_TPL = urllib.parse.urljoin(
    API_BASE, "maps/{map_id}/layers/{layer_id}/finish_upload"
)

# taken from https://gist.github.com/migurski/bc1c5f518f42666801b1973a71703318 
# and extended for one-off examples!
class FeltMap:
    token: str
    map_id: str
    map_url: str
    embed_url: str
    http_headers: dict[str, str]

    def __init__(self, api_token):
        self.token = api_token
        self.http_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
    def createMap(self, title):
        # Create a new Felt map
        resp = requests.post(
            MAPS_URL,
            headers=self.http_headers,
            data=json.dumps({"title": title}),
        )
        assert resp.status_code in range(200, 299)

        self.map_id = resp.json()["data"]["id"]
        self.map_url = resp.json()["data"]["attributes"]["url"]
        self.embed_url = self.map_url.replace("/map/", "/embed/map/")

    def add_layer(self, df: pandas.DataFrame) -> str:
        """Upload DataFrame CSV to Felt Map and return its layer_id"""
        filename = "dataframe.csv"

        progress = IPython.display.ProgressBar(4)
        progress.display()
        next(progress)

        # Ask Felt API to allow a file upload
        resp1 = requests.post(
            LAYERS_TPL.format(map_id=self.map_id),
            headers=self.http_headers,
            json={"file_names": [filename], "name": "DataFrame"},
        )
        assert resp1.status_code in range(200, 299)
        next(progress)

        layer_id = resp1.json()["data"]["attributes"]["layer_id"]
        post_url = resp1.json()["data"]["attributes"]["url"]
        attributes = resp1.json()["data"]["attributes"]["presigned_attributes"]

        # Upload file content using Felt's presigned POST attributes
        with tempfile.TemporaryDirectory() as tempdir:
            filepath = os.path.join(tempdir, filename)
            df.to_csv(filepath)

            with open(filepath, "rb") as file:
                resp2 = requests.post(post_url, files={**attributes, "file": file})
                assert resp2.status_code in range(200, 299)
                next(progress)

        # Notify Felt that file content upload is done
        resp3 = requests.post(
            FINISH_TPL.format(map_id=self.map_id, layer_id=layer_id),
            headers=self.http_headers,
            json={"filename": filename},
        )
        assert resp3.status_code in range(200, 299)
        try:
            next(progress)
        except StopIteration:
            pass

        return layer_id
    
    def pullElements(self, mapId):
        elements_url = API_BASE + 'maps/' + mapId + '/elements'
        print(elements_url)
        response = requests.get(
            elements_url,
            headers = self.http_headers)
        if response.status_code == 200:
            json_data = response.json()
            return json_data
        else:
            print("Failed to retrieve data from the API. Status code:", response.status_code)
            return None
        

    def show(self) -> IPython.display.HTML:
        """Return HTML object for displaying map in IPython"""
        return IPython.display.HTML(
            f"""<iframe
                width="99%"
                height="450px"
                style="border: 1px solid #415125; border-radius: 8px"
                title="Felt Map"
                src="{self.embed_url}"
                referrerpolicy="strict-origin-when-cross-origin"
            ></iframe>"""
        )
