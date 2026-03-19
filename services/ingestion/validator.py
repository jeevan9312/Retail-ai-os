import pandas as pd

def validate_transactions(df: pd.DataFrame) -> dict:
    """Run quality checks on transactions data"""
    
    issues = []
    
    # Check required columns exist
    required_cols = ['transaction_id','store_id','sku_id','quantity','price','timestamp']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        issues.append(f"Missing columns: {missing}")
    
    # Check for nulls in critical fields
    null_counts = df[required_cols].isnull().sum()
    for col, count in null_counts.items():
        if count > 0:
            issues.append(f"Nulls in {col}: {count} rows")
    
    # Check for negative quantities or prices
    if (df['quantity'] <= 0).any():
        issues.append(f"Negative/zero quantity: {(df['quantity']<=0).sum()} rows")
    if (df['price'] <= 0).any():
        issues.append(f"Negative/zero price: {(df['price']<=0).sum()} rows")
    
    return {
        "total_rows":   len(df),
        "issues":       issues,
        "passed":       len(issues) == 0
    }

if __name__ == "__main__":
    df = pd.read_csv("data/raw/transactions.csv")
    result = validate_transactions(df)
    
    print(f"Total rows: {result['total_rows']}")
    print(f"Quality check: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
    for issue in result['issues']:
        print(f"  ⚠️  {issue}")