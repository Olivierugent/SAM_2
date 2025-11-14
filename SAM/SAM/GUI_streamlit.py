"""
Streamlit GUI for PDP Analysis - SAM Version
============================================
Replaces Dash GUI with Streamlit interface.
All functionality from GUI.py but with simpler, more intuitive Streamlit components.

Run with: streamlit run GUI_streamlit.py
"""

import streamlit as st
import os
import sys
import threading
import time
import subprocess
import io
import contextlib
import importlib
from pathlib import Path

# Set page config first (must be first Streamlit command)
st.set_page_config(
    page_title="🚀 PDP Analysis Dashboard",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set environment to skip heavy loading during import
os.environ.setdefault('AV_SKIP_LOAD', '1')

# Import av to get defaults
import av

# Initialize session state for persistent data
if 'run_thread' not in st.session_state:
    st.session_state.run_thread = None
if 'last_status' not in st.session_state:
    st.session_state.last_status = 'idle'
if 'last_output' not in st.session_state:
    st.session_state.last_output = ''
if 'stop_requested' not in st.session_state:
    st.session_state.stop_requested = False
if 'analysis_finished' not in st.session_state:
    st.session_state.analysis_finished = False
if 'log_file_path' not in st.session_state:
    st.session_state.log_file_path = None


def run_moving_objects_in_background(params):
    """
    Background worker function that runs N_Moving_Objects with given parameters.
    Writes output to a log file for real-time monitoring.
    """
    try:
        st.session_state.last_status = 'running'
        st.session_state.last_output = 'Starting analysis...\n'
        st.session_state.analysis_finished = False
        
        # Get results dir first
        results_dir = params.get('results_dir', os.getcwd())
        os.makedirs(results_dir, exist_ok=True)
        
        # Create log file immediately for debugging
        log_file_path = os.path.join(results_dir, 'analysis_log.txt')
        st.session_state.log_file_path = log_file_path
        
        with open(log_file_path, 'w', encoding='utf-8') as debug_log:
            debug_log.write("="*60 + "\n")
            debug_log.write("🔍 DEBUG: Function started\n")
            debug_log.write(f"📂 Results dir: {results_dir}\n")
            debug_log.write(f"📊 Dataset param: {params.get('dataset_name', 'N_C_Dataset.csv')}\n")
            debug_log.write(f"🗂️ Current working dir: {os.getcwd()}\n")
            debug_log.write("="*60 + "\n")
        
        # Validate dataset file exists
        dataset_name = params.get('dataset_name', 'N_C_Dataset.csv')
        if not os.path.isfile(dataset_name):
            with open(log_file_path, 'a', encoding='utf-8') as debug_log:
                debug_log.write(f'❌ ERROR: Dataset file not found: {dataset_name}\n')
                debug_log.write(f'📂 Looking in: {os.path.abspath(dataset_name)}\n')
            st.session_state.last_status = 'error'
            st.session_state.last_output = f'❌ ERROR: Dataset file not found: {dataset_name}'
            return
        
        # Set environment variables for av module
        if 'dataset_name' in params:
            os.environ['AV_DATASET'] = params['dataset_name']
        
        os.environ['AV_RESULTS_DIR'] = results_dir
        
        # Allow av to load dataset now
        os.environ['AV_SKIP_LOAD'] = '0'
        
        # Open log file for writing
        log_file = open(log_file_path, 'a', encoding='utf-8', buffering=1)
        
        # Redirect stdout and stderr to log file
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        class LogWriter:
            def __init__(self, log_file, original):
                self.log_file = log_file
                self.original = original
                
            def write(self, text):
                self.log_file.write(text)
                self.log_file.flush()
                
            def flush(self):
                self.log_file.flush()
        
        sys.stdout = LogWriter(log_file, old_stdout)
        sys.stderr = LogWriter(log_file, old_stderr)
        
        try:
            print("="*60)
            print("🚀 STARTING ANALYSIS")
            print("="*60)
            print(f"📊 Dataset: {params.get('dataset_name', 'N_C_Dataset.csv')}")
            print(f"📂 Results: {results_dir}")
            print("="*60)
            
            # Reload av so it processes the dataset with the provided environment
            import importlib
            importlib.reload(av)
            
            # Apply all parameters to av module
            for key, value in params.items():
                if hasattr(av, key):
                    setattr(av, key, value)
            
            print(f'✅ Configuration loaded successfully')
            print(f'🔢 Configurations: {av.con}, Timestamps: {av.tst}, Points: {av.poi}')
            print('='*60)
            
            # Import and run N_Moving_Objects
            import N_Moving_Objects
            importlib.reload(N_Moving_Objects)
            
            # Check for stop request periodically
            if st.session_state.stop_requested:
                print('\n⏹️ Analysis stopped by user request.')
                st.session_state.last_status = 'stopped'
            else:
                print('\n✅ Analysis completed successfully!')
                st.session_state.last_status = 'finished'
                st.session_state.analysis_finished = True
                
        except Exception as e:
            print(f'\n❌ ERROR during analysis:\n{str(e)}')
            import traceback
            traceback.print_exc()
            st.session_state.last_status = 'error'
        
        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            log_file.close()
            
            # Read final output
            try:
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    st.session_state.last_output = f.read()
            except:
                pass
        
    except Exception as e:
        st.session_state.last_status = 'error'
        st.session_state.last_output = f'❌ CRITICAL ERROR:\n{str(e)}'
    
    finally:
        # Reset environment
        os.environ['AV_SKIP_LOAD'] = '1'
        st.session_state.run_thread = None


# ============================================================================
# MAIN UI
# ============================================================================

# Header
st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 24px; border-radius: 12px; color: white; margin-bottom: 20px;
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);'>
        <h1 style='margin: 0 0 8px 0; font-size: 32px;'>🚀 Moving Objects Analysis Dashboard</h1>
        <p style='font-size: 16px; opacity: 0.95; margin: 0;'>
            ⚙️ Configureer parameters, selecteer modules en start de analyse
        </p>
    </div>
""", unsafe_allow_html=True)

# Create three columns for layout
col1, col2, col3 = st.columns([1, 1, 1])

# ============================================================================
# COLUMN 1: PDP Types & Core Parameters
# ============================================================================
with col1:
    st.markdown("### 📊 PDP Types")
    
    # Fundamental is always required (disabled checkbox)
    st.checkbox("🔹 Fundamental (required)", value=True, disabled=True, key='pdp_fundamental')
    
    # Optional PDP types
    pdp_buffer = st.checkbox("🔸 Buffer", value=av.PDPg_buffer == 1, key='pdp_buffer')
    pdp_rough = st.checkbox("🔶 Rough", value=av.PDPg_rough == 1, key='pdp_rough')
    pdp_bufferrough = st.checkbox("🔷 Buffer + Rough", value=av.PDPg_bufferrough == 1, key='pdp_bufferrough')
    
    st.markdown("### 🔢 Core Parameters")
    window_length_tst = st.number_input("⏱️ window_length_tst", value=av.window_length_tst, min_value=1, step=1)
    
    st.markdown("### 📏 Buffer / Rough Parameters")
    col1a, col1b = st.columns(2)
    with col1a:
        buffer_x = st.number_input("↔️ buffer_x", value=av.buffer_x, disabled=not pdp_buffer and not pdp_bufferrough)
        rough_x = st.number_input("↔️ rough_x", value=av.rough_x, disabled=not pdp_rough and not pdp_bufferrough)
    with col1b:
        buffer_y = st.number_input("↕️ buffer_y", value=av.buffer_y, disabled=not pdp_buffer and not pdp_bufferrough)
        rough_y = st.number_input("↕️ rough_y", value=av.rough_y, disabled=not pdp_rough and not pdp_bufferrough)

# ============================================================================
# COLUMN 2: Visualization & Analysis Modules
# ============================================================================
with col2:
    st.markdown("### 🎨 Visualization & Analysis Modules")
    
    # Create multiselect for all modules
    module_options = {
        'N_PDP': 'PDP Calculation (Distance Matrices)',
        'N_VA_StaticAbsolute': 'Static Absolute',
        'N_VA_HeatMap': 'Heatmap',
        'N_VA_HClust': 'Hierarchical Clustering',
        'N_VA_Mds': 'MDS',
        'N_VA_InequalityMatrices': 'Inequality Matrices',
        'N_VA_TopK': 'Top K',
        'N_VA_TennisCourt': '🎾 Tennis Court',
    }
    
    # Get default selected modules
    default_selected = [k for k, v in module_options.items() if getattr(av, k, 0) == 1]
    
    selected_modules = st.multiselect(
        "Select modules to run:",
        options=list(module_options.keys()),
        default=default_selected,
        format_func=lambda x: module_options[x]
    )
    
    st.markdown("### 💾 Dataset & Output")
    
    # Dataset file selection
    dataset_name = st.text_input("📁 Dataset file (CSV path)", 
                                 value=getattr(av, 'dataset_name', 'N_C_Dataset.csv'),
                                 help="Enter full path to CSV file or use file uploader below")
    
    # File uploader as alternative to text input
    uploaded_file = st.file_uploader("Or upload a CSV file", type=['csv'], key='dataset_uploader')
    if uploaded_file is not None:
        # Save uploaded file to temp location
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            dataset_name = tmp_file.name
            st.success(f"✅ File uploaded: {uploaded_file.name}")
    
    # Results directory selection
    results_dir = st.text_input("📂 Results directory", 
                                value=os.environ.get('AV_RESULTS_DIR', os.getcwd()),
                                help="Enter full path to output directory")
    
    # Quick path suggestions
    with st.expander("💡 Common Paths"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📁 Current Directory"):
                st.info(f"Current: {os.getcwd()}")
            if st.button("📁 User Home"):
                st.info(f"Home: {os.path.expanduser('~')}")
        with col2:
            if st.button("📁 Desktop"):
                desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                st.info(f"Desktop: {desktop}")
            if st.button("📁 Documents"):
                docs = os.path.join(os.path.expanduser('~'), 'Documents')
                st.info(f"Documents: {docs}")

# ============================================================================
# COLUMN 3: Advanced Settings
# ============================================================================
with col3:
    with st.expander("⚙️ Advanced Settings", expanded=False):
        st.markdown("### 🎞️ Interpolation")
        num_frames = st.number_input("num_frames", value=getattr(av, 'num_frames', 20), min_value=1)
        
        st.markdown("### 🗺️ Spatial Bounds")
        col3a, col3b = st.columns(2)
        with col3a:
            min_boundary_x = st.number_input("⬅️ min_x", value=av.min_boundary_x)
            min_boundary_y = st.number_input("⬇️ min_y", value=av.min_boundary_y)
        with col3b:
            max_boundary_x = st.number_input("➡️ max_x", value=av.max_boundary_x)
            max_boundary_y = st.number_input("⬆️ max_y", value=av.max_boundary_y)
        
        st.markdown("### 🔧 Other Parameters")
        DD = st.number_input("📐 DD", value=getattr(av, 'DD', 2), min_value=1)
        des = st.number_input("📊 des", value=getattr(av, 'des', 2), min_value=1)
        dim = st.number_input("📏 dim", value=getattr(av, 'dim', 2), min_value=1)
        
        num_similar_configurations = st.number_input("🔢 num_similar_configurations", 
                                                     value=getattr(av, 'num_similar_configurations', 5), min_value=1)
        new_configuration_step = st.number_input("➕ new_configuration_step", 
                                                 value=getattr(av, 'new_configuration_step', 3), min_value=1)
        division_factor = st.number_input("➗ division_factor", 
                                         value=getattr(av, 'division_factor', 5), min_value=1)

# ============================================================================
# RUN CONTROL SECTION
# ============================================================================
st.markdown("---")
st.markdown("### 🎮 Analysis Control")

col_run1, col_run2, col_run3, col_run4 = st.columns(4)

with col_run1:
    if st.button("▶️ Run Analysis", type="primary", use_container_width=True):
        # Build params dictionary
        params = {
            # PDP types
            'PDPg_fundamental': 1,
            'PDPg_buffer': 1 if pdp_buffer else 0,
            'PDPg_rough': 1 if pdp_rough else 0,
            'PDPg_bufferrough': 1 if pdp_bufferrough else 0,
            'PDPg_fundamental_active': 1,
            'PDPg_buffer_active': 1 if pdp_buffer else 0,
            'PDPg_rough_active': 1 if pdp_rough else 0,
            'PDPg_bufferrough_active': 1 if pdp_bufferrough else 0,
            
            # Visualization modules
            **{k: (1 if k in selected_modules else 0) for k in module_options.keys()},
            
            # Auto-enable dependencies
            'N_PDP': 1 if any(mod in selected_modules for mod in ['N_VA_HeatMap', 'N_VA_HClust', 'N_VA_Mds', 'N_VA_TopK', 'N_VA_InequalityMatrices']) else (1 if 'N_PDP' in selected_modules else 0),
            
            # Numeric parameters
            'window_length_tst': int(window_length_tst),
            'num_frames': int(num_frames),
            'buffer_x': int(buffer_x),
            'buffer_y': int(buffer_y),
            'rough_x': int(rough_x),
            'rough_y': int(rough_y),
            'min_boundary_x': int(min_boundary_x),
            'max_boundary_x': int(max_boundary_x),
            'min_boundary_y': int(min_boundary_y),
            'max_boundary_y': int(max_boundary_y),
            'DD': int(DD),
            'des': int(des),
            'dim': int(dim),
            'num_similar_configurations': int(num_similar_configurations),
            'new_configuration_step': int(new_configuration_step),
            'division_factor': int(division_factor),
            'dataset_name': dataset_name,
            'results_dir': results_dir
        }
        
        # Start analysis in background thread
        if st.session_state.run_thread is None or not st.session_state.run_thread.is_alive():
            st.session_state.stop_requested = False
            
            # DEBUG: Write a test file to verify results_dir is accessible
            try:
                os.makedirs(results_dir, exist_ok=True)
                test_file = os.path.join(results_dir, '_button_clicked.txt')
                with open(test_file, 'w') as f:
                    f.write(f"Button clicked at {time.time()}\n")
                    f.write(f"Dataset: {dataset_name}\n")
                    f.write(f"Results dir: {results_dir}\n")
            except Exception as e:
                st.error(f"DEBUG: Could not create test file: {e}")
            
            st.session_state.run_thread = threading.Thread(
                target=run_moving_objects_in_background, 
                args=(params,), 
                daemon=True
            )
            st.session_state.run_thread.start()
            st.success("✅ Analysis started in background!")
            st.info(f"📂 Check results in: {results_dir}")
            time.sleep(0.5)
            st.rerun()
        else:
            st.warning("⚠️ Analysis already running!")

with col_run2:
    if st.button("⏹️ Stop Analysis", type="secondary", use_container_width=True):
        st.session_state.stop_requested = True
        st.warning("⏹️ Stop requested. Waiting for safe termination point...")
        time.sleep(0.5)
        st.rerun()

with col_run3:
    if st.button("🔄 Refresh Status", use_container_width=True):
        st.rerun()

with col_run4:
    if st.button("📈 View Results", 
                 disabled=not st.session_state.analysis_finished,
                 use_container_width=True):
        # Launch Streamlit viewer
        viewer_path = os.path.abspath(os.path.normpath(
            os.path.join(os.path.dirname(__file__), '..', '..', 'visualisations', 'app_PDP_results.py')
        ))
        
        if os.path.exists(viewer_path):
            env = os.environ.copy()
            env['AV_RESULTS_DIR'] = results_dir
            env['AV_DATASET'] = dataset_name
            
            try:
                subprocess.Popen(
                    [sys.executable, '-m', 'streamlit', 'run', viewer_path],
                    env=env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
                )
                st.success(f"✅ Results viewer launched! Check your browser.")
            except Exception as e:
                st.error(f"❌ Could not launch viewer: {e}")
        else:
            st.error(f"❌ Viewer not found at: {viewer_path}")

# ============================================================================
# STATUS DISPLAY
# ============================================================================
st.markdown("---")
st.markdown("### 📊 Analysis Status")

# Status indicator
status_emoji = {
    'idle': '💤',
    'running': '⚙️',
    'finished': '✅',
    'stopped': '⏹️',
    'error': '❌'
}

status_color = {
    'idle': 'gray',
    'running': 'blue',
    'finished': 'green',
    'stopped': 'orange',
    'error': 'red'
}

current_status = st.session_state.last_status
st.markdown(f"**Status:** :{status_color[current_status]}[{status_emoji[current_status]} {current_status.upper()}]")

# DEBUG: Show log file path and existence
if st.session_state.log_file_path:
    log_exists = os.path.exists(st.session_state.log_file_path)
    st.markdown(f"**Debug:** Log file: `{st.session_state.log_file_path}` (exists: {log_exists})")
    if log_exists:
        try:
            file_size = os.path.getsize(st.session_state.log_file_path)
            st.markdown(f"**Debug:** Log file size: {file_size} bytes")
        except:
            pass

# Auto-refresh while running with helpful info
if current_status == 'running':
    # Read log file for real-time updates
    if st.session_state.log_file_path and os.path.exists(st.session_state.log_file_path):
        try:
            with open(st.session_state.log_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                st.session_state.last_output = content
                st.markdown(f"**Debug:** Read {len(content)} characters from log file")
        except Exception as e:
            st.error(f"⚠️ Error reading log: {e}")
            st.session_state.last_output += f"\n⚠️ Error reading log: {e}"
    else:
        st.warning(f"⚠️ Log file not found: {st.session_state.log_file_path}")
    
    st.info("""
    ⏳ **Analysis running...** 
    - Page auto-refreshes every 1 second
    - Real-time progress updates shown below
    - Timer shows elapsed time and estimated completion
    - TQDM progress bars track each PDP stage
    """)
    
    # Show live output immediately while running
    if st.session_state.last_output:
        st.markdown("### 📟 Live Output")
        # Use code block instead of text_area for better real-time updates
        st.code(st.session_state.last_output, language='text')
    else:
        st.info("⏳ Waiting for analysis to start... (no output yet)")
    
    st.markdown(f"**Debug:** Output length: {len(st.session_state.last_output)} characters")
    
    time.sleep(1)  # Refresh every 1 second
    st.rerun()

# Output display (when not running)
elif st.session_state.last_output:
    with st.expander("📄 Analysis Output", expanded=(current_status in ['finished', 'error'])):
        st.code(st.session_state.last_output, language='text')

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: gray; font-size: 12px;'>
        🎾 SAM Tennis Analysis Module | Built with Streamlit
    </div>
""", unsafe_allow_html=True)
