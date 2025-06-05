import streamlit as st
import pandas as pd
import plotly.express as px
from language_dict import LANGUAGES, MAIN_CATEGORIES, SUB_CATEGORIES, DEWATERING_MACHINE_TYPES, COLUMN_MAP

def load_and_process_data(uploaded_file, lang) -> pd.DataFrame:
    try:
        df = pd.read_excel(uploaded_file)
        columns_to_clean = ['固形物回収率 %', '脱水ケーキ含水率 %']
        for col in columns_to_clean:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].replace(r'^\s*$', pd.NA, regex=True)
        return df
    except Exception as e:
        st.error(LANGUAGES[lang]["error"].format(msg=str(e)))
        return None

def display_boxplot(df, value_col, category_col, show_outliers, lang, T, sorted_categories=None):
    if df is not None and not df.empty:
        points_mode = 'all' if show_outliers else False
        fig = px.box(
            df,
            x=category_col,
            y=value_col,
            points=points_mode,
            title=f"{T[category_col]} - {T[value_col]} Boxplot" if lang == "en" else f"{category_col}ごとの{value_col}の箱ひげ図",
            category_orders={category_col: sorted_categories} if sorted_categories else None
        )
        fig.update_layout(xaxis_tickangle=-45, height=600)
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

def display_summary_chart(df, group_by, lang, T, color_col=None, sorted_categories=None):
    if df is not None and not df.empty:
        if color_col and color_col in df.columns:
            summary = df.groupby([group_by, color_col]).size().reset_index(name='件数')
            summary = summary.sort_values(by=[group_by, '件数'], ascending=[True, False])
        else:
            summary = df[group_by].value_counts().reset_index()
            summary.columns = [group_by, '件数']
        if group_by in summary.columns:
            total_counts = summary.groupby(group_by)['件数'].sum().reset_index()
            sorted_categories = total_counts.sort_values('件数', ascending=False)[group_by].tolist()
        else:
            sorted_categories = summary[group_by].tolist() if group_by in summary.columns else []
        fig = px.bar(
            summary,
            x=group_by,
            y='件数',
            title=f'{T[group_by]} Count' if lang == "en" else f'{group_by}別の件数',
            labels={group_by: '', '件数': 'Count' if lang == "en" else '件数'},
            color=color_col,
            text='件数',
            text_auto=True,
            color_discrete_sequence=px.colors.qualitative.Pastel,
            category_orders={group_by: sorted_categories}
        )
        fig.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig, use_container_width=True)

def map_column_names(df, lang):
    # 只做显示用，不改变原始数据
    col_map = COLUMN_MAP[lang]
    return df.rename(columns=col_map)

def main():
    # 语言选择
    lang = st.sidebar.selectbox("Language / 言語", options=["ja", "en"], format_func=lambda x: "日本語" if x=="ja" else "English")
    T = LANGUAGES[lang]
    st.set_page_config(page_title=T["app_title"], layout="wide")
    st.title(T["app_title"])

    uploaded_file = st.file_uploader(T["upload_label"], type=['xlsx', 'xls'])

    if uploaded_file is not None:
        df = load_and_process_data(uploaded_file, lang)
        if df is not None:
            # 过滤器
            st.header(T["filter_header"])
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                order_status = st.multiselect(
                    T["order_status"],
                    options=[True, False],
                    default=[True, False]
                )
            with col2:
                selected_main_categories = st.multiselect(
                    T["main_category"],
                    options=sorted(MAIN_CATEGORIES[lang]),
                    default=[]
                )
            with col3:
                selected_sub_categories = st.multiselect(
                    T["sub_category"],
                    options=sorted(SUB_CATEGORIES[lang]),
                    default=[]
                )
            with col4:
                selected_machine_types = st.multiselect(
                    T["machine_type"],
                    options=DEWATERING_MACHINE_TYPES[lang],
                    default=[]
                )

            # 数据过滤
            filtered_df = df.copy()
            if order_status:
                filtered_df = filtered_df[filtered_df['受注の有無'].isin(order_status)]
            if selected_main_categories:
                if '業種大分類' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['業種大分類'].isin(selected_main_categories)]
                else:
                    st.warning(T["warning_missing_col"].format(col=T["main_category"]))
                    filtered_df = filtered_df[filtered_df['業種大分類'].isnull()]
            if selected_sub_categories:
                if '業種中分類' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['業種中分類'].isin(selected_sub_categories)]
                else:
                    st.warning(T["warning_missing_col"].format(col=T["sub_category"]))
                    filtered_df = filtered_df[filtered_df['業種中分類'].isnull()]
            if selected_machine_types and '脱水機種別' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['脱水機種別'].isin(selected_machine_types)]
            elif selected_machine_types and '脱水機種別' not in filtered_df.columns:
                st.warning(T["warning_missing_col"].format(col=T["machine_type"]))

            # 分析结果
            st.header(T["analysis_header"])
            st.write(f"{T['total_count']}: {len(filtered_df)}")

            st.subheader(T["chart_subheader"])
            chart_type_options = {
                "ja": ["業種大分類", "業種中分類", "受注の有無"],
                "en": ["業種大分類", "業種中分類", "受注の有無"]
            }
            chart_type = st.radio(
                T["chart_type_select"],
                chart_type_options[lang]
            )
            if chart_type in filtered_df.columns:
                color_col = '脱水機種別' if '脱水機種別' in filtered_df.columns else None
                display_summary_chart(filtered_df, chart_type, lang, T, color_col=color_col)
            else:
                st.warning(T["warning_missing_col"].format(col=chart_type))

            # 数值分析
            st.header(T["boxplot_header"])
            numeric_columns = filtered_df.select_dtypes(include='number').columns.tolist()
            preferred_columns = ["汚泥濃度 TS%", "VTS%/TS", "脱水ケーキ含水率 %", "固形物回収率 %"]
            ordered_numeric_columns = [col for col in preferred_columns if col in numeric_columns]
            ordered_numeric_columns.extend([col for col in numeric_columns if col not in preferred_columns])

            if ordered_numeric_columns:
                col_box1, col_box2 = st.columns(2)
                with col_box1:
                    st.subheader(T["boxplot1"])
                    value_col_main = st.selectbox(T["select_numeric"], ordered_numeric_columns, key="boxplot1_value")
                    show_outliers_main = st.checkbox(T["show_outliers"], value=False, key="outliers_main")
                    show_zeros_main = st.checkbox(T["show_zeros"], value=False, key="show_zeros_main")
                    if '業種大分類' in filtered_df.columns:
                        df_for_analysis_main = filtered_df.copy()
                        columns_to_filter_zero_and_nan = ['固形物回収率 %', '脱水ケーキ含水率 %']
                        if value_col_main in columns_to_filter_zero_and_nan and not show_zeros_main:
                            df_for_analysis_main = df_for_analysis_main[df_for_analysis_main[value_col_main].notna() & (df_for_analysis_main[value_col_main] != 0)]
                        elif value_col_main in columns_to_filter_zero_and_nan and show_zeros_main:
                            df_for_analysis_main = df_for_analysis_main[df_for_analysis_main[value_col_main].notna()]
                        category_counts_main = df_for_analysis_main["業種大分類"].value_counts().reset_index()
                        category_counts_main.columns = ["業種大分類", 'count']
                        sorted_categories_main = category_counts_main.sort_values('count', ascending=False)["業種大分類"].tolist()
                        display_boxplot(df_for_analysis_main, value_col_main, "業種大分類", show_outliers_main, lang, T, sorted_categories=sorted_categories_main)
                        st.markdown("---")
                        st.subheader(T["summary_stats"].format(col=value_col_main, group=T["main_category"]))
                        try:
                            grouped_stats_main = df_for_analysis_main.groupby("業種大分類")[value_col_main].describe()
                            st.dataframe(grouped_stats_main)
                        except Exception as e:
                            st.error(T["error"].format(msg=str(e)))
                    else:
                        st.warning(T["warning_missing_col"].format(col=T["main_category"]))

                with col_box2:
                    st.subheader(T["boxplot2"])
                    value_col_sub = st.selectbox(T["select_numeric"], ordered_numeric_columns, key="boxplot2_value")
                    show_outliers_sub = st.checkbox(T["show_outliers"], value=False, key="outliers_sub")
                    show_zeros_sub = st.checkbox(T["show_zeros"], value=False, key="show_zeros_sub")
                    if '業種中分類' in filtered_df.columns:
                        df_for_analysis_sub = filtered_df.copy()
                        columns_to_filter_zero_and_nan = ['固形物回収率 %', '脱水ケーキ含水率 %']
                        if value_col_sub in columns_to_filter_zero_and_nan and not show_zeros_sub:
                            df_for_analysis_sub = df_for_analysis_sub[df_for_analysis_sub[value_col_sub].notna() & (df_for_analysis_sub[value_col_sub] != 0)]
                        elif value_col_sub in columns_to_filter_zero_and_nan and show_zeros_sub:
                            df_for_analysis_sub = df_for_analysis_sub[df_for_analysis_sub[value_col_sub].notna()]
                        category_counts_sub = df_for_analysis_sub["業種中分類"].value_counts().reset_index()
                        category_counts_sub.columns = ["業種中分類", 'count']
                        sorted_categories_sub = category_counts_sub.sort_values('count', ascending=False)["業種中分類"].tolist()
                        display_boxplot(df_for_analysis_sub, value_col_sub, "業種中分類", show_outliers_sub, lang, T, sorted_categories=sorted_categories_sub)
                        st.markdown("---")
                        st.subheader(T["summary_stats"].format(col=value_col_sub, group=T["sub_category"]))
                        try:
                            grouped_stats_sub = df_for_analysis_sub.groupby("業種中分類")[value_col_sub].describe()
                            st.dataframe(grouped_stats_sub)
                        except Exception as e:
                            st.error(T["error"].format(msg=str(e)))
                    else:
                        st.warning(T["warning_missing_col"].format(col=T["sub_category"]))
            else:
                st.warning(T["no_numeric"])

            # 显示过滤后的数据（列名映射）
            st.header(T["filtered_data"])
            st.dataframe(map_column_names(filtered_df, lang))

if __name__ == "__main__":
    main()
