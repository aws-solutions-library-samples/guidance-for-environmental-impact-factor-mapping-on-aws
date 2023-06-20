from sentence_transformers import (
    SentenceTransformer, util
)

class MLModel:
    def __init__(self, model_name = 'all-mpnet-base-v2'):
        self.model = SentenceTransformer(model_name)
    
    def compute_similarity_scores(self, product_list, naics_list):
        prod_embeddings = self.model.encode(product_list, convert_to_tensor=True)
        naics_embeddings = self.model.encode(naics_list, convert_to_tensor=True)
        cosine_scores = util.pytorch_cos_sim(prod_embeddings, naics_embeddings)
        return cosine_scores
