from db_bigquery import get_card_master

df = get_card_master(limit=10)
print(df.head())
print(df.shape)
print(df.columns.tolist())