#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام إدارة صيانة الأجهزة الطبية - المراكز الصحية
Medical Equipment Maintenance Management System
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import json

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="نظام إدارة الصيانة الطبية",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS مخصص للتصميم ---
st.markdown("""
<style>
    .main {
        direction: rtl;
        text-align: right;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .maintenance-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .alert-red {
        background-color: #ff4b4b;
        padding: 10px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
    }
    .alert-yellow {
        background-color: #ffa500;
        padding: 10px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
    }
    .alert-green {
        background-color: #00cc00;
        padding: 10px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
    }
    div[data-testid="stSidebarNav"] {
        background-color: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)

# --- قائمة المراكز الصحية ---
CENTERS = [
    ("الخلاوية", "KHL-PHC"), ("جبل القهر", "GQH-PHC"), ("مقزع", "MQZ-PHC"),
    ("القوام", "QWM-PHC"), ("الجبل الأسود", "BLM-PHC"), ("السادة", "SAD-PHC"),
    ("بيش الشمالي", "NBS-PHC"), ("قرية بيش", "VBS-PHC"), ("المحلة", "MHL-PHC"),
    ("العشة", "ASH-PHC"), ("أبو السداد", "ASD-PHC"), ("العالية", "ALA-PHC"),
    ("السلامة", "SAL-PHC"), ("مسلية", "MSL-PHC"), ("عتود", "ATD-PHC"),
    ("الفطيحة", "FTH-PHC"), ("منشبة", "MNS-PHC"), ("قايم الدش", "QDS-PHC"),
    ("المطعن", "MTN-PHC"), ("الحقو", "HAQ-PHC"), ("الريث", "RYT-PHC"),
    ("الشقيق", "SHQ-PHC"), ("الدرب", "DRB-PHC"), ("بيش الجنوبي", "SBS-PHC"),
    ("عمود", "AMD-PHC")
]

CENTERS_DICT = {code: name for name, code in CENTERS}
CENTERS_DICT_REV = {name: code for name, code in CENTERS}

# --- دوال مساعدة ---
@st.cache_data
def load_data(file_path):
    """تحميل بيانات الأجهزة من ملف Excel"""
    try:
        df = pd.read_excel(file_path)
        
        # استخراج كود المركز من Asset ID
        df['Center_Code'] = df['Asset ID'].str.split('-').str[0:2].str.join('-')
        df['Center_Name'] = df['Center_Code'].map(CENTERS_DICT)
        
        # تحويل التواريخ
        if 'Installation Date' in df.columns:
            df['Installation Date'] = pd.to_datetime(df['Installation Date'], errors='coerce')
        
        # إضافة أعمدة الصيانة إذا لم تكن موجودة
        if 'Last_Maintenance' not in df.columns:
            df['Last_Maintenance'] = pd.NaT
        else:
            df['Last_Maintenance'] = pd.to_datetime(df['Last_Maintenance'], errors='coerce')
            
        if 'Next_Maintenance' not in df.columns:
            df['Next_Maintenance'] = pd.NaT
        else:
            df['Next_Maintenance'] = pd.to_datetime(df['Next_Maintenance'], errors='coerce')
            
        if 'Maintenance_Interval_Days' not in df.columns:
            df['Maintenance_Interval_Days'] = 90  # افتراضي 3 شهور
            
        if 'Device_Status' not in df.columns:
            df['Device_Status'] = 'عامل'  # عامل، معطل، تحت الصيانة
            
        if 'Priority' not in df.columns:
            df['Priority'] = 'متوسط'  # عالي، متوسط، منخفض
            
        if 'Notes' not in df.columns:
            df['Notes'] = ''
            
        return df
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {e}")
        return None

def calculate_maintenance_status(row):
    """حساب حالة الصيانة للجهاز"""
    today = pd.Timestamp.now()
    
    if pd.isna(row['Next_Maintenance']):
        return "غير محدد", "⚪"
    
    days_until = (row['Next_Maintenance'] - today).days
    
    if days_until < 0:
        return "متأخر", "🔴"
    elif days_until <= 7:
        return "عاجل", "🟠"
    elif days_until <= 30:
        return "قريب", "🟡"
    else:
        return "جيد", "🟢"

def save_data(df, file_path):
    """حفظ البيانات المحدثة"""
    try:
        # حذف الأعمدة المؤقتة قبل الحفظ
        cols_to_drop = ['Center_Code', 'Center_Name']
        df_to_save = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
        df_to_save.to_excel(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"خطأ في حفظ البيانات: {e}")
        return False

def export_maintenance_report(df, center=None):
    """تصدير تقرير الصيانة"""
    if center:
        df_export = df[df['Center_Name'] == center].copy()
    else:
        df_export = df.copy()
    
    # إضافة حالة الصيانة
    df_export['Maintenance_Status'] = df_export.apply(
        lambda row: calculate_maintenance_status(row)[0], axis=1
    )
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, sheet_name='تقرير الصيانة', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['تقرير الصيانة']
        
        # تنسيق العناوين
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white',
            'align': 'center',
            'border': 1
        })
        
        for col_num, value in enumerate(df_export.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20)
    
    output.seek(0)
    return output

# --- الواجهة الرئيسية ---
def main():
    st.title("🏥 نظام إدارة صيانة الأجهزة الطبية")
    st.markdown("---")
    
    # الشريط الجانبي
    with st.sidebar:
        st.image("https://via.placeholder.com/200x80/4CAF50/FFFFFF?text=وزارة+الصحة", use_container_width=True)
        st.markdown("### القائمة الرئيسية")
        
        menu = st.radio(
            "اختر القسم:",
            ["📊 لوحة المعلومات", "📋 إدارة الأجهزة", "🔧 جدولة الصيانة", 
             "📈 التقارير والإحصائيات", "⚙️ الإعدادات"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.info("💡 **نصيحة**: استخدم الفلاتر لتخصيص العرض حسب احتياجاتك")
    
    # تحميل البيانات
    if 'df' not in st.session_state:
        df = load_data('/mnt/user-data/uploads/All_Devices_Merged.xlsx')
        if df is not None:
            st.session_state.df = df
        else:
            st.error("فشل تحميل البيانات!")
            return
    
    df = st.session_state.df
    
    # --- لوحة المعلومات ---
    if menu == "📊 لوحة المعلومات":
        show_dashboard(df)
    
    # --- إدارة الأجهزة ---
    elif menu == "📋 إدارة الأجهزة":
        show_devices_management(df)
    
    # --- جدولة الصيانة ---
    elif menu == "🔧 جدولة الصيانة":
        show_maintenance_schedule(df)
    
    # --- التقارير والإحصائيات ---
    elif menu == "📈 التقارير والإحصائيات":
        show_reports(df)
    
    # --- الإعدادات ---
    elif menu == "⚙️ الإعدادات":
        show_settings(df)

def show_dashboard(df):
    """عرض لوحة المعلومات الرئيسية"""
    st.header("📊 لوحة المعلومات الشاملة")
    
    # الفلاتر
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_centers = st.multiselect(
            "اختر المراكز:",
            options=sorted(df['Center_Name'].dropna().unique()),
            default=None
        )
    
    with col2:
        selected_departments = st.multiselect(
            "اختر الأقسام:",
            options=sorted(df['Scientific Department'].dropna().unique()),
            default=None
        )
    
    with col3:
        status_filter = st.multiselect(
            "حالة الجهاز:",
            options=['عامل', 'معطل', 'تحت الصيانة'],
            default=['عامل']
        )
    
    # تطبيق الفلاتر
    df_filtered = df.copy()
    if selected_centers:
        df_filtered = df_filtered[df_filtered['Center_Name'].isin(selected_centers)]
    if selected_departments:
        df_filtered = df_filtered[df_filtered['Scientific Department'].isin(selected_departments)]
    if status_filter:
        df_filtered = df_filtered[df_filtered['Device_Status'].isin(status_filter)]
    
    st.markdown("---")
    
    # المؤشرات الرئيسية
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🏥 إجمالي الأجهزة",
            value=len(df_filtered),
            delta=f"{len(df_filtered[df_filtered['Device_Status']=='عامل'])} عامل"
        )
    
    with col2:
        overdue = len(df_filtered[
            (df_filtered['Next_Maintenance'] < pd.Timestamp.now()) & 
            (df_filtered['Next_Maintenance'].notna())
        ])
        st.metric(
            label="🔴 صيانات متأخرة",
            value=overdue,
            delta="يحتاج اهتمام" if overdue > 0 else "ممتاز",
            delta_color="inverse"
        )
    
    with col3:
        urgent = len(df_filtered[
            ((df_filtered['Next_Maintenance'] - pd.Timestamp.now()).dt.days <= 7) & 
            (df_filtered['Next_Maintenance'] >= pd.Timestamp.now()) &
            (df_filtered['Next_Maintenance'].notna())
        ])
        st.metric(
            label="🟠 صيانات عاجلة",
            value=urgent,
            delta="خلال 7 أيام"
        )
    
    with col4:
        broken = len(df_filtered[df_filtered['Device_Status'] == 'معطل'])
        st.metric(
            label="⚠️ أجهزة معطلة",
            value=broken,
            delta=f"{(broken/len(df_filtered)*100):.1f}%" if len(df_filtered) > 0 else "0%"
        )
    
    st.markdown("---")
    
    # الرسوم البيانية
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 توزيع الأجهزة حسب المراكز")
        center_counts = df_filtered['Center_Name'].value_counts().head(10)
        fig = px.bar(
            x=center_counts.values,
            y=center_counts.index,
            orientation='h',
            labels={'x': 'عدد الأجهزة', 'y': 'المركز'},
            color=center_counts.values,
            color_continuous_scale='Viridis'
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🔧 حالة الصيانة")
        df_filtered['Maintenance_Status'] = df_filtered.apply(
            lambda row: calculate_maintenance_status(row)[0], axis=1
        )
        status_counts = df_filtered['Maintenance_Status'].value_counts()
        
        colors = {
            'متأخر': '#ff4b4b',
            'عاجل': '#ffa500',
            'قريب': '#ffeb3b',
            'جيد': '#4caf50',
            'غير محدد': '#9e9e9e'
        }
        
        fig = go.Figure(data=[go.Pie(
            labels=status_counts.index,
            values=status_counts.values,
            marker=dict(colors=[colors.get(x, '#cccccc') for x in status_counts.index]),
            hole=0.4
        )])
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # جدول الأجهزة التي تحتاج صيانة عاجلة
    st.subheader("🚨 أجهزة تحتاج صيانة فورية")
    urgent_devices = df_filtered[
        ((df_filtered['Next_Maintenance'] - pd.Timestamp.now()).dt.days <= 7) &
        (df_filtered['Next_Maintenance'].notna())
    ].sort_values('Next_Maintenance')
    
    if len(urgent_devices) > 0:
        display_cols = ['Asset ID', 'Scientific Equipment Name', 'Center_Name', 
                       'Next_Maintenance', 'Device_Status', 'Priority']
        st.dataframe(
            urgent_devices[display_cols].head(10),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ لا توجد أجهزة تحتاج صيانة عاجلة!")

def show_devices_management(df):
    """إدارة الأجهزة"""
    st.header("📋 إدارة الأجهزة")
    
    tab1, tab2, tab3 = st.tabs(["🔍 بحث وعرض", "➕ إضافة جهاز", "✏️ تعديل/حذف"])
    
    with tab1:
        st.subheader("البحث عن الأجهزة")
        
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("🔍 بحث (الاسم، الرقم التسلسلي، الموديل):")
        with col2:
            center_filter = st.selectbox(
                "المركز:",
                ['الكل'] + sorted(df['Center_Name'].dropna().unique().tolist())
            )
        
        # تطبيق البحث
        df_search = df.copy()
        if search_term:
            df_search = df_search[
                df_search['Scientific Equipment Name'].str.contains(search_term, case=False, na=False) |
                df_search['Serial No'].astype(str).str.contains(search_term, case=False, na=False) |
                df_search['Model'].astype(str).str.contains(search_term, case=False, na=False)
            ]
        if center_filter != 'الكل':
            df_search = df_search[df_search['Center_Name'] == center_filter]
        
        st.write(f"النتائج: {len(df_search)} جهاز")
        
        if len(df_search) > 0:
            # عرض النتائج
            display_df = df_search[[
                'Asset ID', 'Scientific Equipment Name', 'Manufacturer', 
                'Model', 'Center_Name', 'Device_Status', 'Next_Maintenance'
            ]].copy()
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # تصدير النتائج
            excel_data = export_maintenance_report(df_search)
            st.download_button(
                label="📥 تحميل النتائج (Excel)",
                data=excel_data,
                file_name=f"devices_search_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with tab2:
        st.subheader("إضافة جهاز جديد")
        
        with st.form("add_device_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                center = st.selectbox("المركز*:", sorted(df['Center_Name'].dropna().unique()))
                equipment_name = st.text_input("اسم الجهاز*:")
                manufacturer = st.text_input("الشركة المصنعة:")
                model = st.text_input("الموديل:")
            
            with col2:
                department = st.selectbox(
                    "القسم*:",
                    sorted(df['Scientific Department'].dropna().unique())
                )
                serial_no = st.text_input("الرقم التسلسلي:")
                installation_date = st.date_input("تاريخ التركيب:")
                device_status = st.selectbox("حالة الجهاز:", ['عامل', 'معطل', 'تحت الصيانة'])
            
            maintenance_interval = st.number_input(
                "فترة الصيانة (بالأيام):", 
                min_value=7, 
                max_value=365, 
                value=90
            )
            
            priority = st.selectbox("الأولوية:", ['عالي', 'متوسط', 'منخفض'])
            notes = st.text_area("ملاحظات:")
            
            submitted = st.form_submit_button("➕ إضافة الجهاز", use_container_width=True)
            
            if submitted:
                if equipment_name and center and department:
                    # توليد Asset ID جديد
                    center_code = CENTERS_DICT_REV[center]
                    existing_ids = df[df['Center_Code'] == center_code]['Asset ID'].tolist()
                    max_num = 0
                    for asset_id in existing_ids:
                        try:
                            num = int(asset_id.split('-')[-1])
                            max_num = max(max_num, num)
                        except:
                            pass
                    new_asset_id = f"{center_code}-{max_num+1:03d}"
                    
                    # إضافة الجهاز الجديد
                    new_row = {
                        'Asset ID': new_asset_id,
                        'Scientific Department': department,
                        'Scientific Equipment Name': equipment_name,
                        'Manufacturer': manufacturer,
                        'Model': model,
                        'Serial No': serial_no,
                        'PPM Done': None,
                        'Installation Date': pd.Timestamp(installation_date),
                        'Status': None,
                        'Center_Code': center_code,
                        'Center_Name': center,
                        'Last_Maintenance': pd.NaT,
                        'Next_Maintenance': pd.Timestamp(installation_date) + timedelta(days=maintenance_interval),
                        'Maintenance_Interval_Days': maintenance_interval,
                        'Device_Status': device_status,
                        'Priority': priority,
                        'Notes': notes
                    }
                    
                    st.session_state.df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    
                    if save_data(st.session_state.df, '/mnt/user-data/uploads/All_Devices_Merged.xlsx'):
                        st.success(f"✅ تم إضافة الجهاز بنجاح! Asset ID: {new_asset_id}")
                        st.rerun()
                    else:
                        st.error("❌ فشل حفظ البيانات")
                else:
                    st.error("⚠️ يرجى ملء جميع الحقول المطلوبة (*)")
    
    with tab3:
        st.subheader("تعديل أو حذف جهاز")
        
        asset_id = st.selectbox(
            "اختر الجهاز للتعديل:",
            df['Asset ID'].tolist()
        )
        
        if asset_id:
            device = df[df['Asset ID'] == asset_id].iloc[0]
            
            with st.form("edit_device_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    equipment_name = st.text_input("اسم الجهاز:", value=device['Scientific Equipment Name'])
                    manufacturer = st.text_input("الشركة المصنعة:", value=str(device['Manufacturer']))
                    model = st.text_input("الموديل:", value=str(device['Model']))
                
                with col2:
                    device_status = st.selectbox(
                        "حالة الجهاز:", 
                        ['عامل', 'معطل', 'تحت الصيانة'],
                        index=['عامل', 'معطل', 'تحت الصيانة'].index(device['Device_Status']) if device['Device_Status'] in ['عامل', 'معطل', 'تحت الصيانة'] else 0
                    )
                    priority = st.selectbox(
                        "الأولوية:", 
                        ['عالي', 'متوسط', 'منخفض'],
                        index=['عالي', 'متوسط', 'منخفض'].index(device['Priority']) if device['Priority'] in ['عالي', 'متوسط', 'منخفض'] else 1
                    )
                    maintenance_interval = st.number_input(
                        "فترة الصيانة (بالأيام):", 
                        min_value=7, 
                        max_value=365, 
                        value=int(device['Maintenance_Interval_Days'])
                    )
                
                notes = st.text_area("ملاحظات:", value=str(device['Notes']) if pd.notna(device['Notes']) else '')
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    update_btn = st.form_submit_button("💾 حفظ التعديلات", use_container_width=True)
                with col_btn2:
                    delete_btn = st.form_submit_button("🗑️ حذف الجهاز", use_container_width=True, type="secondary")
                
                if update_btn:
                    idx = df[df['Asset ID'] == asset_id].index[0]
                    st.session_state.df.loc[idx, 'Scientific Equipment Name'] = equipment_name
                    st.session_state.df.loc[idx, 'Manufacturer'] = manufacturer
                    st.session_state.df.loc[idx, 'Model'] = model
                    st.session_state.df.loc[idx, 'Device_Status'] = device_status
                    st.session_state.df.loc[idx, 'Priority'] = priority
                    st.session_state.df.loc[idx, 'Maintenance_Interval_Days'] = maintenance_interval
                    st.session_state.df.loc[idx, 'Notes'] = notes
                    
                    if save_data(st.session_state.df, '/mnt/user-data/uploads/All_Devices_Merged.xlsx'):
                        st.success("✅ تم حفظ التعديلات بنجاح!")
                        st.rerun()
                    else:
                        st.error("❌ فشل حفظ التعديلات")
                
                if delete_btn:
                    if st.checkbox("⚠️ أنا متأكد من حذف هذا الجهاز"):
                        st.session_state.df = st.session_state.df[st.session_state.df['Asset ID'] != asset_id]
                        
                        if save_data(st.session_state.df, '/mnt/user-data/uploads/All_Devices_Merged.xlsx'):
                            st.success("✅ تم حذف الجهاز بنجاح!")
                            st.rerun()
                        else:
                            st.error("❌ فشل حذف الجهاز")

def show_maintenance_schedule(df):
    """جدولة الصيانة"""
    st.header("🔧 جدولة وإدارة الصيانة")
    
    tab1, tab2, tab3 = st.tabs(["📅 جدول الصيانة", "✅ تسجيل صيانة", "📊 إحصائيات الصيانة"])
    
    with tab1:
        st.subheader("جدول الصيانة القادم")
        
        # فلاتر
        col1, col2, col3 = st.columns(3)
        with col1:
            time_range = st.selectbox(
                "الفترة الزمنية:",
                ['متأخر', 'خلال أسبوع', 'خلال شهر', 'خلال 3 شهور', 'الكل']
            )
        with col2:
            priority_filter = st.multiselect(
                "الأولوية:",
                ['عالي', 'متوسط', 'منخفض'],
                default=['عالي', 'متوسط']
            )
        with col3:
            center_filter = st.selectbox(
                "المركز:",
                ['الكل'] + sorted(df['Center_Name'].dropna().unique().tolist())
            )
        
        # تطبيق الفلاتر
        df_schedule = df[df['Next_Maintenance'].notna()].copy()
        
        today = pd.Timestamp.now()
        if time_range == 'متأخر':
            df_schedule = df_schedule[df_schedule['Next_Maintenance'] < today]
        elif time_range == 'خلال أسبوع':
            df_schedule = df_schedule[
                (df_schedule['Next_Maintenance'] >= today) &
                (df_schedule['Next_Maintenance'] <= today + timedelta(days=7))
            ]
        elif time_range == 'خلال شهر':
            df_schedule = df_schedule[
                (df_schedule['Next_Maintenance'] >= today) &
                (df_schedule['Next_Maintenance'] <= today + timedelta(days=30))
            ]
        elif time_range == 'خلال 3 شهور':
            df_schedule = df_schedule[
                (df_schedule['Next_Maintenance'] >= today) &
                (df_schedule['Next_Maintenance'] <= today + timedelta(days=90))
            ]
        
        if priority_filter:
            df_schedule = df_schedule[df_schedule['Priority'].isin(priority_filter)]
        
        if center_filter != 'الكل':
            df_schedule = df_schedule[df_schedule['Center_Name'] == center_filter]
        
        # إضافة حالة الصيانة
        df_schedule['Status_Icon'] = df_schedule.apply(
            lambda row: calculate_maintenance_status(row)[1], axis=1
        )
        df_schedule['Days_Until'] = (df_schedule['Next_Maintenance'] - today).dt.days
        
        # ترتيب حسب الأولوية والموعد
        df_schedule = df_schedule.sort_values(['Priority', 'Next_Maintenance'], 
                                             ascending=[False, True])
        
        st.write(f"عدد الأجهزة: {len(df_schedule)}")
        
        if len(df_schedule) > 0:
            display_cols = ['Status_Icon', 'Asset ID', 'Scientific Equipment Name', 
                          'Center_Name', 'Next_Maintenance', 'Days_Until', 'Priority']
            
            st.dataframe(
                df_schedule[display_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Status_Icon": st.column_config.TextColumn("الحالة", width="small"),
                    "Days_Until": st.column_config.NumberColumn("الأيام المتبقية", format="%d يوم"),
                    "Next_Maintenance": st.column_config.DateColumn("موعد الصيانة", format="DD/MM/YYYY")
                }
            )
            
            # تصدير الجدول
            excel_data = export_maintenance_report(df_schedule)
            st.download_button(
                label="📥 تحميل جدول الصيانة (Excel)",
                data=excel_data,
                file_name=f"maintenance_schedule_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("لا توجد أجهزة تطابق معايير البحث")
    
    with tab2:
        st.subheader("تسجيل صيانة منجزة")
        
        asset_id = st.selectbox(
            "اختر الجهاز:",
            df['Asset ID'].tolist(),
            key="maintenance_asset_select"
        )
        
        if asset_id:
            device = df[df['Asset ID'] == asset_id].iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**الجهاز:** {device['Scientific Equipment Name']}")
                st.info(f"**المركز:** {device['Center_Name']}")
            with col2:
                if pd.notna(device['Next_Maintenance']):
                    st.info(f"**الصيانة القادمة:** {device['Next_Maintenance'].strftime('%Y-%m-%d')}")
                else:
                    st.warning("لم يتم تحديد موعد صيانة")
            
            with st.form("maintenance_log_form"):
                maintenance_date = st.date_input(
                    "تاريخ الصيانة:",
                    value=datetime.now()
                )
                
                maintenance_type = st.selectbox(
                    "نوع الصيانة:",
                    ['صيانة دورية', 'صيانة طارئة', 'معايرة', 'إصلاح عطل', 'استبدال قطع']
                )
                
                technician = st.text_input("اسم الفني:")
                
                maintenance_notes = st.text_area("ملاحظات الصيانة:")
                
                parts_replaced = st.text_area("القطع المستبدلة:")
                
                device_status_after = st.selectbox(
                    "حالة الجهاز بعد الصيانة:",
                    ['عامل', 'معطل', 'تحت الصيانة']
                )
                
                next_maintenance_interval = st.number_input(
                    "موعد الصيانة القادمة (بعد كم يوم):",
                    min_value=7,
                    max_value=365,
                    value=int(device['Maintenance_Interval_Days'])
                )
                
                submitted = st.form_submit_button("💾 حفظ سجل الصيانة", use_container_width=True)
                
                if submitted:
                    idx = df[df['Asset ID'] == asset_id].index[0]
                    
                    # تحديث البيانات
                    st.session_state.df.loc[idx, 'Last_Maintenance'] = pd.Timestamp(maintenance_date)
                    st.session_state.df.loc[idx, 'Next_Maintenance'] = pd.Timestamp(maintenance_date) + timedelta(days=next_maintenance_interval)
                    st.session_state.df.loc[idx, 'Device_Status'] = device_status_after
                    st.session_state.df.loc[idx, 'Maintenance_Interval_Days'] = next_maintenance_interval
                    
                    # تحديث الملاحظات
                    current_notes = str(device['Notes']) if pd.notna(device['Notes']) else ''
                    new_note = f"\n[{maintenance_date}] {maintenance_type} - {technician}: {maintenance_notes}"
                    st.session_state.df.loc[idx, 'Notes'] = current_notes + new_note
                    
                    if save_data(st.session_state.df, '/mnt/user-data/uploads/All_Devices_Merged.xlsx'):
                        st.success(f"✅ تم تسجيل الصيانة بنجاح! الصيانة القادمة: {(pd.Timestamp(maintenance_date) + timedelta(days=next_maintenance_interval)).strftime('%Y-%m-%d')}")
                        st.rerun()
                    else:
                        st.error("❌ فشل حفظ البيانات")
    
    with tab3:
        st.subheader("إحصائيات الصيانة")
        
        # تحليل الصيانة
        col1, col2, col3 = st.columns(3)
        
        with col1:
            completed = len(df[df['Last_Maintenance'].notna()])
            st.metric("✅ صيانات منجزة", completed)
        
        with col2:
            pending = len(df[
                (df['Next_Maintenance'] < pd.Timestamp.now()) &
                (df['Next_Maintenance'].notna())
            ])
            st.metric("⏰ صيانات متأخرة", pending)
        
        with col3:
            upcoming = len(df[
                (df['Next_Maintenance'] >= pd.Timestamp.now()) &
                (df['Next_Maintenance'] <= pd.Timestamp.now() + timedelta(days=30)) &
                (df['Next_Maintenance'].notna())
            ])
            st.metric("📅 صيانات قادمة (30 يوم)", upcoming)
        
        # رسم بياني للصيانة حسب المراكز
        st.subheader("📊 الصيانة المتأخرة حسب المراكز")
        
        overdue_by_center = df[
            (df['Next_Maintenance'] < pd.Timestamp.now()) &
            (df['Next_Maintenance'].notna())
        ].groupby('Center_Name').size().sort_values(ascending=True)
        
        if len(overdue_by_center) > 0:
            fig = px.bar(
                x=overdue_by_center.values,
                y=overdue_by_center.index,
                orientation='h',
                labels={'x': 'عدد الأجهزة', 'y': 'المركز'},
                color=overdue_by_center.values,
                color_continuous_scale='Reds'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("✅ لا توجد صيانات متأخرة!")

def show_reports(df):
    """التقارير والإحصائيات"""
    st.header("📈 التقارير والإحصائيات")
    
    tab1, tab2, tab3 = st.tabs(["📊 تقرير شامل", "🏥 تقرير المراكز", "📋 تقارير مخصصة"])
    
    with tab1:
        st.subheader("التقرير الشامل للأجهزة والصيانة")
        
        # إحصائيات عامة
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("إجمالي الأجهزة", len(df))
            st.metric("الأجهزة العاملة", len(df[df['Device_Status'] == 'عامل']))
        
        with col2:
            st.metric("الأجهزة المعطلة", len(df[df['Device_Status'] == 'معطل']))
            st.metric("تحت الصيانة", len(df[df['Device_Status'] == 'تحت الصيانة']))
        
        with col3:
            overdue = len(df[
                (df['Next_Maintenance'] < pd.Timestamp.now()) &
                (df['Next_Maintenance'].notna())
            ])
            st.metric("صيانات متأخرة", overdue, delta=f"{(overdue/len(df)*100):.1f}%")
        
        with col4:
            avg_interval = df['Maintenance_Interval_Days'].mean()
            st.metric("متوسط فترة الصيانة", f"{avg_interval:.0f} يوم")
        
        st.markdown("---")
        
        # توزيع الأجهزة
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 توزيع الأجهزة حسب القسم")
            dept_counts = df['Scientific Department'].value_counts().head(10)
            fig = px.pie(
                values=dept_counts.values,
                names=dept_counts.index,
                hole=0.4
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🔧 حالة الأجهزة")
            status_counts = df['Device_Status'].value_counts()
            fig = go.Figure(data=[go.Bar(
                x=status_counts.index,
                y=status_counts.values,
                marker_color=['#4caf50', '#ff4b4b', '#ffa500']
            )])
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        # تصدير التقرير الشامل
        st.markdown("---")
        excel_data = export_maintenance_report(df)
        st.download_button(
            label="📥 تحميل التقرير الشامل (Excel)",
            data=excel_data,
            file_name=f"comprehensive_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with tab2:
        st.subheader("تقرير المراكز الصحية")
        
        selected_center = st.selectbox(
            "اختر المركز:",
            sorted(df['Center_Name'].dropna().unique())
        )
        
        if selected_center:
            df_center = df[df['Center_Name'] == selected_center]
            
            st.markdown(f"### 🏥 {selected_center}")
            st.markdown("---")
            
            # إحصائيات المركز
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("إجمالي الأجهزة", len(df_center))
            
            with col2:
                working = len(df_center[df_center['Device_Status'] == 'عامل'])
                st.metric("أجهزة عاملة", working, delta=f"{(working/len(df_center)*100):.1f}%")
            
            with col3:
                broken = len(df_center[df_center['Device_Status'] == 'معطل'])
                st.metric("أجهزة معطلة", broken, delta=f"{(broken/len(df_center)*100):.1f}%")
            
            with col4:
                overdue = len(df_center[
                    (df_center['Next_Maintenance'] < pd.Timestamp.now()) &
                    (df_center['Next_Maintenance'].notna())
                ])
                st.metric("صيانات متأخرة", overdue)
            
            st.markdown("---")
            
            # جدول الأجهزة
            st.subheader("قائمة الأجهزة")
            display_cols = ['Asset ID', 'Scientific Equipment Name', 'Scientific Department',
                          'Device_Status', 'Next_Maintenance', 'Priority']
            st.dataframe(df_center[display_cols], use_container_width=True, hide_index=True)
            
            # تصدير تقرير المركز
            excel_data = export_maintenance_report(df_center, selected_center)
            st.download_button(
                label=f"📥 تحميل تقرير {selected_center} (Excel)",
                data=excel_data,
                file_name=f"report_{selected_center}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with tab3:
        st.subheader("تقارير مخصصة")
        
        st.info("اختر معايير التقرير المطلوب:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_centers = st.multiselect(
                "المراكز:",
                sorted(df['Center_Name'].dropna().unique()),
                default=None
            )
            
            report_departments = st.multiselect(
                "الأقسام:",
                sorted(df['Scientific Department'].dropna().unique()),
                default=None
            )
        
        with col2:
            report_status = st.multiselect(
                "حالة الجهاز:",
                ['عامل', 'معطل', 'تحت الصيانة'],
                default=['عامل', 'معطل', 'تحت الصيانة']
            )
            
            report_priority = st.multiselect(
                "الأولوية:",
                ['عالي', 'متوسط', 'منخفض'],
                default=['عالي', 'متوسط', 'منخفض']
            )
        
        # تطبيق الفلاتر
        df_custom = df.copy()
        if report_centers:
            df_custom = df_custom[df_custom['Center_Name'].isin(report_centers)]
        if report_departments:
            df_custom = df_custom[df_custom['Scientific Department'].isin(report_departments)]
        if report_status:
            df_custom = df_custom[df_custom['Device_Status'].isin(report_status)]
        if report_priority:
            df_custom = df_custom[df_custom['Priority'].isin(report_priority)]
        
        st.write(f"**عدد الأجهزة في التقرير:** {len(df_custom)}")
        
        if len(df_custom) > 0:
            st.dataframe(
                df_custom[['Asset ID', 'Scientific Equipment Name', 'Center_Name', 
                          'Device_Status', 'Next_Maintenance']],
                use_container_width=True,
                hide_index=True
            )
            
            excel_data = export_maintenance_report(df_custom)
            st.download_button(
                label="📥 تحميل التقرير المخصص (Excel)",
                data=excel_data,
                file_name=f"custom_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def show_settings(df):
    """الإعدادات"""
    st.header("⚙️ إعدادات النظام")
    
    tab1, tab2, tab3 = st.tabs(["🔄 الصيانة الدورية", "📧 الإشعارات", "💾 النسخ الاحتياطي"])
    
    with tab1:
        st.subheader("إعدادات الصيانة الدورية الافتراضية")
        
        st.info("قم بتعيين فترات الصيانة الافتراضية لأنواع الأجهزة المختلفة")
        
        equipment_types = df['Scientific Equipment Name'].dropna().unique()
        
        selected_equipment = st.selectbox(
            "اختر نوع الجهاز:",
            sorted(equipment_types)
        )
        
        if selected_equipment:
            devices = df[df['Scientific Equipment Name'] == selected_equipment]
            current_interval = devices['Maintenance_Interval_Days'].mode()[0] if len(devices) > 0 else 90
            
            new_interval = st.number_input(
                f"فترة الصيانة لـ {selected_equipment} (بالأيام):",
                min_value=7,
                max_value=365,
                value=int(current_interval)
            )
            
            if st.button("✅ تطبيق على جميع الأجهزة من هذا النوع"):
                mask = st.session_state.df['Scientific Equipment Name'] == selected_equipment
                st.session_state.df.loc[mask, 'Maintenance_Interval_Days'] = new_interval
                
                # تحديث مواعيد الصيانة القادمة
                for idx in st.session_state.df[mask].index:
                    last_maint = st.session_state.df.loc[idx, 'Last_Maintenance']
                    if pd.notna(last_maint):
                        st.session_state.df.loc[idx, 'Next_Maintenance'] = last_maint + timedelta(days=new_interval)
                
                if save_data(st.session_state.df, '/mnt/user-data/uploads/All_Devices_Merged.xlsx'):
                    st.success(f"✅ تم تحديث فترة الصيانة لـ {len(devices)} جهاز")
                    st.rerun()
    
    with tab2:
        st.subheader("إعدادات الإشعارات")
        
        st.info("💡 يمكن إضافة نظام إشعارات عبر البريد الإلكتروني أو SMS في المستقبل")
        
        notify_days_before = st.slider(
            "إرسال إشعار قبل موعد الصيانة بـ:",
            min_value=1,
            max_value=30,
            value=7,
            help="سيتم إرسال إشعار تذكيري قبل هذا العدد من الأيام"
        )
        
        notify_overdue = st.checkbox("إرسال إشعار للصيانات المتأخرة", value=True)
        
        notify_email = st.text_input("البريد الإلكتروني للإشعارات:")
        
        if st.button("💾 حفظ إعدادات الإشعارات"):
            st.success("✅ تم حفظ الإعدادات (سيتم تفعيلها في التحديثات القادمة)")
    
    with tab3:
        st.subheader("النسخ الاحتياطي واستعادة البيانات")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💾 نسخ احتياطي")
            if st.button("إنشاء نسخة احتياطية الآن", use_container_width=True):
                backup_data = export_maintenance_report(df)
                st.download_button(
                    label="📥 تحميل النسخة الاحتياطية",
                    data=backup_data,
                    file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
        with col2:
            st.markdown("### 📤 استعادة البيانات")
            uploaded_backup = st.file_uploader(
                "اختر ملف النسخة الاحتياطية:",
                type=['xlsx']
            )
            
            if uploaded_backup:
                if st.button("⚠️ استعادة البيانات", use_container_width=True):
                    try:
                        restored_df = pd.read_excel(uploaded_backup)
                        st.session_state.df = restored_df
                        st.success("✅ تم استعادة البيانات بنجاح!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ في استعادة البيانات: {e}")

# --- تشغيل البرنامج ---
if __name__ == "__main__":
    main()
