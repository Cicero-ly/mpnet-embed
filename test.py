import banana_dev as banana
import os
import pprint
pp = pprint.PrettyPrinter(indent=4)

api_key = os.environ["BANANA_API_KEY"]
model_key = os.environ["BANANA_MODEL_KEY"]
model_inputs = { 
  "prompt" : [
    "I am made of gold.",
    "This box is covered in gold.",
    "That is a gold ingot."
  ]
}

if __name__ == "__main__":
  out = banana.run(api_key, model_key, model_inputs)
  pp.pprint(out)