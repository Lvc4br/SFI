#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    io::{BufRead, BufReader},
    process::{Child, Command, Stdio},
    sync::Mutex,
};

use tauri::{path::BaseDirectory, Manager, RunEvent};

struct ApiRuntime {
    child: Mutex<Option<Child>>,
    base_url: String,
}

fn start_local_api(app: &tauri::App) -> Result<ApiRuntime, Box<dyn std::error::Error>> {
    let data_dir = app.path().app_local_data_dir()?;
    std::fs::create_dir_all(&data_dir)?;

    let bundled_executable = app.path().resolve("sfi-api.exe", BaseDirectory::Resource)?;
    let mut command = if bundled_executable.is_file() {
        Command::new(bundled_executable)
    } else {
        // Development fallback: uses the repository's Python environment.
        let api_root = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../../services/api");
        let python = std::env::var_os("SFI_PYTHON").unwrap_or_else(|| "python".into());
        let mut command = Command::new(python);
        command
            .args(["-m", "sfi_api.desktop_runtime"])
            .current_dir(&api_root)
            .env("PYTHONPATH", api_root.join("src"));
        command
    };

    let mut child = command
        .env("SFI_DATA_DIR", &data_dir)
        .env("SFI_ENVIRONMENT", "desktop")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()?;

    let stdout = child.stdout.take().ok_or("stdout do backend não foi iniciado")?;
    let mut reader = BufReader::new(stdout);
    let mut startup_line = String::new();
    if reader.read_line(&mut startup_line)? == 0 {
        let _ = child.kill();
        let _ = child.wait();
        return Err("O backend local encerrou antes de informar a porta.".into());
    }

    let port = startup_line
        .trim()
        .strip_prefix("SFI_API_READY ")
        .and_then(|value| value.parse::<u16>().ok());

    let Some(port) = port else {
        let _ = child.kill();
        let _ = child.wait();
        return Err("O backend local não concluiu a inicialização.".into());
    };

    Ok(ApiRuntime {
        child: Mutex::new(Some(child)),
        base_url: format!("http://127.0.0.1:{port}"),
    })
}

fn main() {
    let app = tauri::Builder::default()
        .setup(|app| {
            let runtime = start_local_api(app)?;
            app.manage(runtime);
            Ok(())
        })
        .on_page_load(|webview, _payload| {
            let runtime = webview.state::<ApiRuntime>();
            let script = format!(
                "window.__SFI_API_BASE_URL__ = {:?};",
                runtime.base_url
            );
            if let Err(error) = webview.eval(&script) {
                eprintln!("Não foi possível configurar a API local do SFI: {error}");
            }
        })
        .build(tauri::generate_context!())
        .expect("falha ao iniciar o SFI Desktop");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(runtime) = handle.try_state::<ApiRuntime>() {
                if let Ok(mut child_guard) = runtime.child.lock() {
                    if let Some(mut child) = child_guard.take() {
                        let _ = child.kill();
                        let _ = child.wait();
                    }
                }
            }
        }
    });
}
