@echo off 
echo Starting Inventory Management System...  
echo.  
echo Starting Backend API...  
start "Backend API" cmd /k "cd backend && python main.py"  
echo.  
echo Waiting 5 seconds for backend to start...  
timeout /t 5 /nobreak  
echo.  
echo Starting Frontend UI...  
start "Frontend UI" cmd /k "cd frontend && streamlit run main.py"  
echo.  
echo System started! Check the opened windows.  
pause 
