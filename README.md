# HED-COLD Dataset

This dataset is associated with our EMNLP 2025 main conference paper *Enhancing Chinese Offensive Language Detection with Homophonic Perturbation*: https://aclanthology.org/2025.emnlp-main.1154/

**HED-COLD** (Homophonic and Syntactic Enhanced Chinese Offensive Language Dataset) is a Chinese offensive language detection dataset enhanced with homophonic perturbations and syntactic rewriting, based on the original COLD dataset.

## 📊 Dataset Statistics

| Split | Samples | Label=1 (Offensive) | Label=0 (Non-offensive) |
|-------|---------|---------------------|-------------------------|
| Training | 6,300 | 3,227 (51.2%) | 3,073 (48.8%) |
| Development | 700 | 360 (51.4%) | 340 (48.6%) |
| Test | 3,000 | 1,526 (50.9%) | 1,474 (49.1%) |
| **Total** | **10,000** | **5,113 (51.1%)** | **4,887 (48.9%)** |

### Test Set Topic Distribution

| Topic | Samples | Label=1 | Label=0 |
|-------|---------|---------|---------|
| Race | 604 | 311 | 293 |
| Gender | 1,206 | 612 | 594 |
| Region | 1,190 | 603 | 587 |

## 🎯 Dataset Features

1. **Homophonic Perturbation**: 67.8% of samples contain homophonic character substitutions (e.g., 黑人→嘿人, 男权→男拳, 东北→冻倍)
2. **Syntactic Rewriting**: Some samples include syntactic structure adjustments for diversity
3. **Semantic Preservation**: All perturbed samples maintain semantic similarity ≥ 0.6 with original text
4. **Traceability**: Every sample can be traced back to the original COLD dataset

## 📁 File Structure

```
HED-COLD-Dataset/
├── dataset/
│   ├── train.csv          # Training set (6,300 samples)
│   ├── dev.csv            # Development set (700 samples)
│   └── test.csv           # Test set (3,000 samples)
├── traceability/
│   ├── sampled_train_data.csv    # Training set with original text
│   ├── sampled_dev_data.csv      # Development set with original text
│   └── sampled_test_data.csv     # Test set with original text
└── README.md
```

## 📝 Data Format

### Dataset Files (dataset/)

CSV format with the following fields:

- `id`: Unique sample identifier (1-10000)
- `split`: Dataset split (train/dev/test)
- `topic`: Offensive language category (race/gender/region)
- `label`: Label (0=non-offensive, 1=offensive)
- `TEXT`: Text content

**Example:**
```csv
id,split,topic,label,TEXT
1,train,race,0,由于中亚是黄种人白种人冲突的前沿...
2,train,race,1,突然理解了微博视频上美国嘿人抢劫...
```

### Traceability Files (traceability/)

The three files in this folder are directly sampled from the original COLD dataset. 
Each entry corresponds one-to-one with a sample in HED-COLD (by `new_id`), 
allowing users to align the perturbed text with its original version for training, comparison, or robustness analysis.

CSV format with additional fields for tracing back to original COLD dataset:

- `new_id`: New ID in HED-COLD (1-10000)
- `original_id`: Original ID in COLD dataset
- `unique_idx`: Unique index in merged dataset
- `topic`: Topic category
- `label`: Label
- `TEXT`: Text content (original text before perturbation)

Each `new_id` matches exactly one sample in `dataset/`, ensuring strict one-to-one alignment between original and perturbed data.


## 📈 Perturbation Examples

### Race-related
```
Original: 讨厌黑人，更讨厌这种女人
Perturbed: 讨厌嘿人，更讨厌这种女人
```

### Gender-related
```
Original: 屌丝直男癌，黄种人里面的国男人渣
Perturbed: 屌丝直男岸，黄种人里面的国男人渣
```

### Region-related
```
Original: 终于在知乎看到我大四川的香肠了！
Perturbed: 终于在知乎看到我大四穿的香肠了！
```

## 🎓 Use Cases

1. **Robustness Testing**: Evaluate model resistance to homophonic perturbations
2. **Adversarial Training**: Improve model robustness using HED-COLD
3. **Perturbation Detection**: Research methods to identify and restore perturbed text
4. **Cross-domain Generalization**: Evaluate model performance across different offensive language categories

## 📜 Citation

If you use this dataset, please cite:

```bibtex
@inproceedings{HED-COLD,
  title = "Enhancing Chinese Offensive Language Detection with Homophonic Perturbation",
  author = "Wu, Junqi and Ji, Shujie and Zhong, Kang and Peng, Huiling and Zhendongxiao and Liu, Xiongding and Wei, Wu",
  booktitle = "Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing",
  month = nov,
  year = "2025",
  address = "Suzhou, China",
  publisher = "Association for Computational Linguistics",
  url = "https://aclanthology.org/2025.emnlp-main.1154/",
  doi = "10.18653/v1/2025.emnlp-main.1154",
  pages = "22660--22675"
}
```

Original COLD dataset:
```bibtex
@article{deng2022cold,
  title="Cold: A benchmark for chinese offensive language detection",
  author= "Deng, Jiawen and Zhou, Jingyan and Sun, Hao and Mi, Fei and Huang, Minlie",
  booktitle = "Proceedings of the 2022 Conference on Empirical Methods in Natural Language Processing",
  month = dec,
  year = "2022",
  address = "Abu Dhabi, United Arab Emirates",
  publisher = "Association for Computational Linguistics",
  url = "https://aclanthology.org/2022.emnlp-main.796",
  pages = "11580--11599"
}
```

## 🙏 Acknowledgments

This dataset is built upon the open-source [COLD (Chinese Offensive Language Dataset)](https://github.com/thu-coai/COLDataset).  
We sincerely thank the original authors for making the dataset publicly available and for their valuable contribution to the research community.

## 📄 License

This dataset is released under the MIT License.
