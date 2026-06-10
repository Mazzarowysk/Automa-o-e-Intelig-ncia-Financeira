import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

class ModeloXGBoost:
    """Classe especializada em XGBoost com otimização"""
    
    def __init__(self, df, features, target_col='target'):
        self.df = df
        self.features = features
        self.target_col = target_col
        self.modelo = None
        self.scaler = None
        self.metricas = {}
        
    def preparar_dados(self, test_size=0.2):
        X = self.df[self.features].copy()
        y = self.df[self.target_col].copy()
        
        mask = ~(X.isnull().any(axis=1) | y.isnull())
        X = X[mask]
        y = y[mask]
        
        split_idx = int(len(X) * (1 - test_size))
        
        X_train = X.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_test = y.iloc[split_idx:]
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return X_train_scaled, X_test_scaled, y_train, y_test
    
    def treinar_xgboost_base(self, X_train, y_train, X_test, y_test):
        print("🚀 Treinando XGBoost (Otimizado)...")
        xgb = XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.01,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
            early_stopping_rounds=50,
            eval_metric='mae'
        )
        
        tscv = TimeSeriesSplit(n_splits=5)
        
        try:
            cv_scores = cross_val_score(xgb, X_train, y_train, cv=tscv, scoring='neg_mean_absolute_error', n_jobs=-1)
            cv_r2 = cross_val_score(xgb, X_train, y_train, cv=tscv, scoring='r2', n_jobs=-1)
        except:
            cv_scores = np.array([0])
            cv_r2 = np.array([0])
            
        eval_set = [(X_test, y_test)]
        xgb.fit(X_train, y_train, eval_set=eval_set, verbose=False)
        y_pred = xgb.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        direcao = np.mean(np.sign(y_test) == np.sign(y_pred))
        
        self.metricas['XGBoost Base'] = {
            'MAE': mae,
            'RMSE': rmse,
            'R²': r2,
            'Acurácia': direcao,
            'CV_MAE_medio': -cv_scores.mean() if len(cv_scores) > 0 else 0,
            'CV_R2_medio': cv_r2.mean() if len(cv_r2) > 0 else 0,
            'modelo': xgb,
            'y_pred': y_pred
        }
        
        self.modelo = xgb
        print(f"✅ Acurácia Direcional: {direcao*100:.1f}% | MAE: {mae:.4f} | RMSE: {rmse:.4f} | R²: {r2:.4f}")
        return xgb

    def prever(self, precos_atuais=None):
        print("🔮 Gerando previsões...")
        
        ultimos_dias = self.df.tail(30).copy()
        
        if precos_atuais is not None and isinstance(precos_atuais, pd.Series):
            ultimos_dias['Close'] = precos_atuais.values[-30:]
            
        X_futuro = ultimos_dias[self.features].copy()
        mask = ~X_futuro.isnull().any(axis=1)
        X_futuro = X_futuro[mask]
        
        if len(X_futuro) == 0:
            print("⚠️ Sem dados válidos para previsão")
            return None
            
        X_futuro_scaled = self.scaler.transform(X_futuro)
        
        melhor_nome = max(self.metricas.keys(), key=lambda k: self.metricas[k]['Acurácia'])
        melhor_modelo = self.metricas[melhor_nome]['modelo']
        
        previsoes_pct = melhor_modelo.predict(X_futuro_scaled)
        
        previsoes_finais = previsoes_pct[-10:]
        
        # Obter a ultima data e gerar proximos 10 dias uteis
        if 'Date' in self.df.columns:
            ultima_data = pd.to_datetime(self.df['Date'].max())
        else:
            ultima_data = pd.Timestamp.now()
        
        # pd.bdate_range garante apenas dias uteis (segunda a sexta)
        futuras_datas = pd.bdate_range(start=ultima_data + pd.Timedelta(days=1), periods=10)
        
        resultados = []
        for i in range(len(previsoes_finais)):
            idx_real = X_futuro.index[-(10-i)]
            preco_base = ultimos_dias.loc[idx_real, 'Close']
            prev_pct = previsoes_finais[i]
            preco_previsto = preco_base * (1 + prev_pct/100)
            
            data_str = futuras_datas[i].strftime('%Y-%m-%d %H:%M:%S')
            
            resultados.append({
                'Data': data_str,
                'Preco_Base': preco_base,
                'Previsao_Pct': prev_pct,
                'Preco_Previsto': preco_previsto,
                'Modelo': melhor_nome,
                'Confianca': self.metricas[melhor_nome]['Acurácia'] * 100
            })
            
        return pd.DataFrame(resultados)
