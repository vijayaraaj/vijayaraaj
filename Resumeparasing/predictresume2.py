#WORKING-1(resume)
import argparse
import cv2
from PIL import Image
import pytesseract
import json
from ultralytics.yolo.engine.predictor import BasePredictor
from ultralytics.yolo.engine.results import Results
from ultralytics.yolo.utils import DEFAULT_CFG, ROOT, ops
import torch
import os
import easyocr  # Import the easyocr library
import cv2
def extract_text(image):
    # Perform OCR
    reader = easyocr.Reader(['en'])
    result = reader.readtext(image)

    # Post-process to concatenate words that are close together
    combined_text = ""
    prev_x = None
    for detection in result:
        text, confidence = detection[1], detection[2]
        if confidence >= 0.5:  # Adjust the confidence threshold as needed
            combined_text += " " + text

    return combined_text.strip()

class TextDetectionPredictor(BasePredictor):
    def __init__(self, *args, **kwargs):
        super(TextDetectionPredictor, self).__init__(*args, **kwargs)
        self.text_results = []  # List to store extracted text for each image group

    def postprocess(self, preds, img, orig_imgs):
        preds = ops.non_max_suppression(preds,
                                        self.args.conf,
                                        self.args.iou,
                                        agnostic=self.args.agnostic_nms,
                                        max_det=self.args.max_det,
                                        classes=self.args.classes)
        results = []
        for i, pred in enumerate(preds):
            orig_img = orig_imgs[i] if isinstance(orig_imgs, list) else orig_imgs
            if not isinstance(orig_imgs, torch.Tensor):
                pred[:, :4] = ops.scale_boxes(img.shape[2:], pred[:, :4], orig_img.shape)
            path = self.batch[0]
            img_path = path[i] if isinstance(path, list) else path
            results.append(Results(orig_img=orig_img, path=img_path, names=self.model.names, boxes=pred))

            # Sort the bounding boxes by their top-left y-coordinate (y1)
            pred = pred[pred[:, 1].argsort()]
            fulltext = extract_text(orig_img)  # Extract text from the whole image
            # Extract text from bounding boxes in the order they appear
            text_info = []  # List to store text information for each field
            for box in pred:
                x1, y1, x2, y2, conf, cls = box.tolist()
                bbox_img = orig_img[int(y1):int(y2), int(x1):int(x2)]
                text = extract_text(bbox_img)
                class_name = self.model.names[int(cls)]
                text_info.append({"class_name": class_name, "text": text})

            image_group = {
                "image_path": img_path,
                "data": [{"fulltext": fulltext, "text_fields": text_info}],
            }
            self.text_results.append(image_group)

        return results


    def save_text_results(self, save_path):
        with open(save_path, 'w') as f:
            json.dump({"data": self.text_results}, f, indent=4)

    def print_text_results(self, output_file=None):
        output = ""
        for image_group in self.text_results:
            output += image_group["image_path"] + "\n"
            for text_dict in image_group["data"]:
                for class_name, texts in text_dict.items():
                    output += f"{class_name}:\n"
                    for i, text in enumerate(texts):
                        output += f"Text {i + 1}: {text}\n"
                    output += "\n"
   
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='YOLO prediction script')
    parser.add_argument('--weights', type=str, default='yolov8n.pt', dest='model', help='Path to the weights file')
    parser.add_argument('--source', type=str, default='https://ultralytics.com/images/bus.jpg',
                        help='Path to the image folder or URL')
    parser.add_argument('--output', type=str, default=None, help='Path to the output file')
    args = parser.parse_args()

    predictor = TextDetectionPredictor(overrides={'model': args.model, 'source': args.source})
    results = predictor.predict_cli()

    # Save the text dictionary as JSON
    save_path = os.path.join(os.path.dirname(args.model), 'text_results.json')
    predictor.save_text_results(save_path)
    print(f"Text results saved to: {save_path}")
    
    import json
    from difflib import SequenceMatcher
    
    # Function to calculate similarity between two strings
    def similarity(a, b):
        return SequenceMatcher(None, a, b).ratio()
    
    # Load the JSON data from the input file
    with open(save_path, "r") as f:
        json_data = json.load(f)
    
   

    import json
    from difflib import SequenceMatcher
    
    # Function to calculate similarity between two strings
    def similarity(a, b):
        return SequenceMatcher(None, a, b).ratio()
    
    
    
    # Load the JSON data from the input file
    with open(save_path, "r") as f:
        json_data = json.load(f)
    
    # Create a dictionary to store combined data
    combined_data = {}
    
    # Define a threshold for matching image path names
    path_name_threshold = 0.9
    
    # Iterate through the data and combine based on similar image path names
    for entry in json_data["data"]:
        image_path = entry["image_path"]
        
        found_similar = False
        
        for existing_path, combined_entry in combined_data.items():
            if similarity(image_path, existing_path) > path_name_threshold:
                combined_entry["data"].extend(entry["data"])
                found_similar = True
                break
        
        if not found_similar:
            combined_data[image_path] = {
                "data": entry["data"]
            }
    
    # Create a new list of combined objects
    combined_list = [{"image_path": image_path, "data": combined_entry["data"]}
                     for image_path, combined_entry in combined_data.items()]
    
    # Create a new JSON object with the combined data
    combined_json = {"data": combined_list}
    
    # Specify the output JSON file path
    output_file_path = save_path  # Replace with the desired output file path
    
    # Write the combined JSON data to the output file
    with open(output_file_path, "w") as f:
        json.dump(combined_json, f, indent=4)
    
    # Print a message indicating the data has been written to the file
    print(f"Combined JSON data written to {output_file_path}")
    

    # Print the extracted text
    predictor.print_text_results(output_file=args.output)
