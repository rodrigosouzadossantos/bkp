import pandas as pd
from sklearn.metrics import f1_score, accuracy_score, recall_score, classification_report,  precision_score


def remove_columns_dataframe(dataframe_predict: pd.core.frame.DataFrame, columns_to_remove: list)-> list:
    """
        Remove as colunas do drataframe
        Parametros:
            dataframe_predict: Dataframe com as predições
            columns_to_remove: Lista com as colunas que serão removidas
        Retorno: Uma lista com o nome das colunas do dataframe após a remoção de colunas indesejáeis
    """
    pred_classes = dataframe_predict.columns.to_list()
    for column in columns_to_remove:
        if column in pred_classes:
            pred_classes.remove(column)
    
    return pred_classes

def select_common_columns_dataframes(trues_dataframe: pd.core.frame.DataFrame, preds_dataframe: pd.core.frame.DataFrame)-> (pd.core.frame.DataFrame, pd.core.frame.DataFrame):
    """
        Selecione apenas as colunas do dataframe de trues iguais as colunas do dataframe de predições, fazendo com que ambos os dataframes fiquem com as mesmas colunas
        Parametros:
            trues_dataframe: Dataframe com dados verdadeiros
            preds_dataframe: Dataframe com os resultados das predições
        Retorno: Dataframes com as mesmas colunas
    """
    common_columns = trues_dataframe.columns.intersection(preds_dataframe.columns)
    print(common_columns)
    trues_dataframe= trues_dataframe.loc[preds_dataframe.index, common_columns]
    preds_dataframe = preds_dataframe.loc[preds_dataframe.index, common_columns]
    
    return trues_dataframe, preds_dataframe

def f1_recall_precision_metrics(trues_dataframe: pd.core.frame.DataFrame, preds_dataframe: pd.core.frame.DataFrame)->(float, float, float):
    """
        Calcula as métricas f1 score e recall para as predições do modelo
        Parametros:
            trues_dataframe: Dataframe com dados verdadeiros
            preds_dataframe: Dataframe com os resultados das predições
        Retorno: As métricas f1 score e recall
            
    """
    f1_total = f1_score(trues_dataframe, preds_dataframe, average='samples', zero_division=1)
    
    recall = recall_score(trues_dataframe, preds_dataframe, average='samples', zero_division=1)
    
    precision = precision_score(trues_dataframe, preds_dataframe, average='samples', zero_division=1)
    
    
    return f1_total, recall, precision

def classification_report_per_class(list_class: list, number_class: int, trues_dataframe: pd.core.frame.DataFrame, preds_dataframe: pd.core.frame.DataFrame)-> pd.core.frame.DataFrame:
    """
        Gera um classification Report com as métricas por classe
        Parametros:
            list_class: lista com as classes
            number_class: Número de classes
            trues_dataframe: Dataframe com dados verdadeiros
            preds_dataframe: Dataframe com os resultados das predições
        Retorno: Dataframe com as métricas por classe
        
    """
    
    report = classification_report(trues_dataframe, preds_dataframe)
    linhas = report.split('\n')
    precision = []
    recall = []
    f1 = []
    support = []
    classes = []

    # Criando um dicionário para mapear os números de classe para os rótulos de classe
    mapeamento_classes = {}
    for i in range(number_class):  # Supondo que você tenha 29 classes
        mapeamento_classes[str(i)] = list_class[i]

    # Lista para armazenar as linhas processadas
    linhas_processadas = []
    # Substituindo os números de classe pelos rótulos de classe reais nas linhas do classification_report
    for linha in linhas:
        tokens = linha.split()

        if tokens and tokens[0] in mapeamento_classes:        
            precision.append(tokens[1])
            recall.append(tokens[2])
            f1.append(tokens[3])
            support.append(tokens[4])
            tokens[0] = mapeamento_classes[tokens[0]]
            classes.append(tokens[0])
            linhas_processadas.append(tokens)
        else:
            #print(tokens)
            linhas_processadas.append(tokens)

    # Convertendo as linhas processadas em um DataFrame
    result_pd = pd.DataFrame({'classe': classes, 'precisao': precision, 'recall': recall, 'f1_score': f1, 'support': support})

    # Exibindo o DataFrame
    print(result_pd)
    
    return result_pd