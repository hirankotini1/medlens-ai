# Live Project Demonstration Script (5–10 Minutes)

A step-by-step presentation script with exact actions and talking points for a live project demonstration during a college project review, viva, or technical evaluation.

---

## Preparation Before Starting
1. Start the backend server:
   ```bash
   python -m uvicorn disease_prediction.api.main:app --host 127.0.0.1 --port 8000
   ```
2. Open **`http://127.0.0.1:8000/`** in a clean browser window (e.g. Chrome).
3. Have the terminal open in the background to show test executions if requested.

---

## Demonstration Flow & Talking Points

### Step 1: Landing Page & Project Introduction (1 Minute)
* **Action:** Show the homepage at `http://127.0.0.1:8000/`.
* **Talking Points:**
  > *"Respected evaluators, this is **Nexus Pathology**, a digital pathology laboratory management platform combined with an experimental machine-learning decision-support module. Traditional pathology systems often suffer from fragmented paper records, lack of secure patient access, and absence of computational assistance. Nexus Pathology digitizes this workflow while establishing a safe, decoupled architecture where ML predictions never alter official medical records."*
  > *"Notice that right from the landing page, we prominently display our educational and research disclaimer, stating that AI predictions serve as decision support and do not constitute an autonomous medical diagnosis."*

---

### Step 2: Administrative Portal & Report Creation (2 Minutes)
* **Action:** Click **`[Lab Staff / Admin]`** in the top navigation bar. Enter `admin` / `admin123` and click **`Authenticate Staff Session`**.
* **Talking Points:**
  > *"First, let's explore the Administrative Portal. When lab technicians or pathologists log in, they are greeted by an operational dashboard displaying summary metrics: Total Registered Patients, Total Laboratory Reports, Finalized Reports, and Active ML Pipelines."*
  > *"Let's demonstrate creating an official report. I'll click **`+ Create Lab Report`**. Notice our smart form design: when I switch the test panel between Anemia CBC, Dengue, Liver, or Thyroid, the interface dynamically renders **only** the relevant parameters for that specific investigation, complete with biological reference intervals and clinical units."*
  > *"Reports can be saved as a **Draft** during technician review, or **Finalized** as a locked official medical record."*

---

### Step 3: Running Experimental ML Decision Support (1.5 Minutes)
* **Action:** In the reports table, click **`⚡ Run ML`** on Report `REP-2026-001` (Anemia CBC).
* **Talking Points:**
  > *"Now, let's execute our Experimental ML Decision Support. When we trigger analysis, the backend retrieves the structured laboratory metrics, validates all required features, and routes them through our validated Logistic Regression pipeline."*
  > *"Notice how the result is displayed: it appears in a **completely separate, visually decoupled card**. It shows the classification output ('Anemic'), calculated model confidence (98.5%), an Elevated Risk pill, the model version, and an explicit disclaimer. The official laboratory report above remains 100% immutable and uncorrupted."*

---

### Step 4: Patient Portal & Strict Patient Isolation (2 Minutes)
* **Action:** Click **`[Patient Portal]`** in the top navigation. Click the one-click demo button **`PAT-1001 (Anemia CBC)`** and click **`Access Dashboard`**.
* **Talking Points:**
  > *"Now let's see the patient experience. The patient logs in with their Patient ID and Security PIN. Once authenticated, they enter their personalized Patient Dashboard."*
  > *"Here, the patient sees their demographic summary, total reports on file, and their list of laboratory investigations. When they view their report, they see an accredited pathology sheet with clear color-coded status badges—Normal, Low, High, Critical—and the pathologist's remarks."*
  > *"Patients can also click **`🖨️ Print Official Report`** to generate a clean, print-ready document formatted with dedicated print stylesheets."*
  > *"Crucially, our security architecture enforces **strict patient isolation (IDOR protection)**: Patient A can only access their own reports. If an unauthorized user attempts to manipulate the URL or API to request another patient's data, our FastAPI backend rejects it with an immediate **HTTP 403 Forbidden**."*

---

### Step 5: Direct ML Sandbox & Malaria Microscopy Upload (2 Minutes)
* **Action:** Click **`[ML Decision Support]`** in the top navigation. Switch between the tabular diseases, then click **`🔬 Malaria (Microscopy)`**. Select or drag a blood smear image and click **`Run Malaria ML Pipeline`**.
* **Talking Points:**
  > *"In addition to report-linked analysis, we provide a Direct ML Sandbox for exploratory testing across all five models. For Malaria, we implemented an image classification pipeline. Users can upload a Giemsa-stained thin blood smear cell image. The backend validates the image (5MB limit, MIME check, OpenCV decodability), extracts a 354-dimensional color and texture feature vector, and classifies it using Gradient Boosting with **94.03% accuracy and 97.80% recall**."*

---

### Step 6: Security Verification & Conclusion (1.5 Minutes)
* **Action:** (Optional) Show the terminal with the 25 passing automated tests.
* **Talking Points:**
  > *"To verify the system, we built an automated test suite of **25 distinct test scenarios** covering security defenses (IDOR, SQL injection, malicious image rejection), integration workflows, and report immutability, achieving a **100% pass rate**."*
  > *"We also conducted a controlled synthetic data experiment which proved that real baseline clinical data outperformed synthetic augmentations, leading to our decision to keep the original validated models in production."*
  > *"In summary, Nexus Pathology bridges the gap between digital laboratory management and responsible, transparent AI decision support. Thank you, and we welcome any questions."*
