import pandas as pd
import numpy as np
import math
import argparse
import logging
import warnings
from timeit import default_timer as timestamp


from pandas.core.common import SettingWithCopyWarning
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=SettingWithCopyWarning)

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold, KFold, train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score
from catboost import CatBoostClassifier

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--learning_rate',
                      type = float,
                      default = 0.143242,
                      help = 'Step size shrinkage used in update to prevent overfitting.')
  parser.add_argument('--max_depth',
                      type = int,
                      default = 10,
                      help = 'Maximum depth of a tree.')
  parser.add_argument('--n_estimators',
                      type = int,
                      default = 800 ,
                      help = 'Number of trees to fit.')
  parser.add_argument('--use_best_model',
                      type = bool,
                      default = True ,
                      help = '')
  parser.add_argument('--allow_writing_files',
                      type = bool,
                      default = False ,
                      help = '')
  parser.add_argument('--metric_period',
                      type = int,
                      default = 20 ,
                      help = '')
  parser.add_argument('--verbose',
                      type = bool,
                      default = False ,
                      help = '')
  args = parser.parse_args()

  # Load data
  all_data=pd.read_csv('https://raw.githubusercontent.com/Josepholaidepetro/Umojahack/main/maven/Train.csv')
  # print("all_data size is : {}".format(all_data.shape))

  # Convert date columns to datetime datatypes 
  for i in all_data.columns:
    if i[-4:] == 'Date':
      all_data[str(i)] = pd.to_datetime(all_data[str(i)],infer_datetime_format=True, errors='coerce')

  # noticed some strange occurence in the age column, as regarding the max and min
  # pre-processing the age column
  all_data['Age'].loc[all_data['Age'] < 0] = all_data['Age'].loc[all_data['Age'] < 0] * -1
  all_data['Age'] = np.where(all_data['Age'] == 320, 120, all_data['Age'])
  all_data['Age'] = np.where(all_data['Age'] > 320, 99, all_data['Age'])

  all_data['Date diff'] = (all_data['Policy End Date'].dt.year - all_data['Policy Start Date'].dt.year) * 12 \
  + (all_data['Policy End Date'].dt.month - all_data['Policy Start Date'].dt.month)

  # Extract Date features
  date_col = ['Policy Start Date', 'Policy End Date', 'First Transaction Date']

  def extract_date_info(df,cols):
    for feat in cols:
        df[feat +'_day'] = df[feat].dt.day
        df[feat +'_month'] = df[feat].dt.month
        df[feat +'_quarter'] = df[feat].dt.quarter
    df.drop(columns=date_col,axis=1,inplace=True)

  extract_date_info(all_data,date_col)

  # deal_missing_data
  # copy data
  all_data1 = all_data.copy()

  # categorical and continuous features
  cat_feat = all_data1.select_dtypes(exclude = np.number).columns
  num_feat = all_data1.select_dtypes(exclude = object).columns

  # Deal with missing values
  for col in num_feat:
    if col != 'target':
      all_data1[col].fillna(-999, inplace = True)  
      
  for col in cat_feat:
    all_data1[col].fillna('NONE', inplace = True)
    
 # feat_engineering
  all_data1['LGA_Name'] = all_data1['LGA_Name'].map(all_data1['LGA_Name'].value_counts().to_dict())
  all_data1['State'] = all_data1['State'].map(all_data1['State'].value_counts().to_dict())
  all_data1['Subject_Car_Make'] = all_data1['Subject_Car_Make'].map(all_data1['Subject_Car_Make'].value_counts().to_dict())
  all_data1['Subject_Car_Colour'] = all_data1['Subject_Car_Colour'].map(all_data1['Subject_Car_Colour'].value_counts().to_dict()) 
  mapper = {"Male":"M","Female":'F','Entity':'O','Joint Gender':'O',None:'O','NO GENDER':'O','NOT STATED':'O','SEX':'O', np.nan: 'O' }
  all_data1.Gender = all_data1.Gender.map(mapper)

  # encode_variable
  for i in ['ProductName', 'Car_Category']:
    encoder = LabelEncoder()
    all_data1[i] = encoder.fit_transform(all_data1[i])

  # feat engineering with the encoded variable
  all_data1['no_pol_prod_name'] = all_data1['No_Pol'] + all_data1['ProductName']

  # drop columns
  all_data1.drop(columns=['ID', 'Subject_Car_Colour'],inplace=True)
  # convert columns with categorical columns to numbers
  all_data1=pd.get_dummies(all_data1)

  # modelling_data
  #Get the train dataset
  train_n = all_data1.copy()
  X= train_n.drop(columns=['target'])
  y= train_n.target
  X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=44)

  # training and validation
  model=CatBoostClassifier(verbose=args.verbose,
      max_depth=args.max_depth,
      learning_rate=args.learning_rate, 
      n_estimators=args.n_estimators)
  start = timestamp()
  model.fit(X_train, y_train)
  stop = timestamp()
  predictions = model.predict(X_test)

  print('time=%.3f' % (stop - start))
  print('accuracy=%.3f' % (accuracy_score(predictions, y_test)))