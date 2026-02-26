To run for testing: open the Command Prompt and type python demo.py and go through the demo.
It will create UBO's (cryptographically sealed decision files created by the UAS) and the Aletheia cryptographically sealed verification files. Both are .json files.
Tampering of either file will break the seal, showing as "tampered" in the audit dashboard.
After running the demo, run python audit_dash.py this will create an html dashboard for viewing the paired files for audit. The dashboard will show "PASS" or "FAIL" for each pair, as well as show if the seals are verified or have been tampered with. Good seals show a green check, tampered seals show a red X.
The dashboard gives an easy, non-technical way for auditors to review decisions while also allowing those more tech-savvy to see the actual json outputs and hashes and seals.
If, for curiosity, you want to see the how they stand up to stress testing, you can run the stress test with python stress_testing.py
Test definitions are in the test_defs.txt file. 
The test definitions were tailored to max on my system (Intel N95 1.7GHz 4Core, 4Thread 64 bit system with 16GB or RAM). If you have better hardware, feel free to tailor the test definitions to work with your system.
The aletheia_v2_standalone.py file is the Aletheia Protocol.
The uas_v2.py is the UAS.
