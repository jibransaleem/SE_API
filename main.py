from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime
from pydantic import EmailStr, ValidationError
from fastapi.responses import JSONResponse
from database import Base, engine
from database import SessionLocal
from models import User, LostItem, Claim
from auth_models import (
    UserCreate,
    UserLogin,
    LostItemCreate,
    LostItemResponse,
    LostItemUpdate,
    ClaimCreate,
    ClaimResponse
)
from email_helper import send_email
import base64

# ---------------- FastAPI Setup ----------------
app = FastAPI(title="CEP Lost & Found API")
Base.metadata.create_all(bind=engine)

# ---------------- Password Hashing ----------------
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# ---------------- Database Dependency ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- Helper Function for Model Serialization ----------------
def serialize_item(item: LostItem) -> dict:
    """Convert LostItem ORM object to dict with proper date handling and base64 image"""
    # Convert image blob to base64 string
    image_base64 = None
    if item.item_image:
        image_base64 = base64.b64encode(item.item_image).decode('utf-8')
    
    return {
        "id": item.id,
        "user_id": item.user_id,
        "item_type": item.item_type,
        "item_name": item.item_name,
        "item_description": item.item_description,
        "item_image": image_base64,  # Base64 encoded image
        "email": item.email,
        "date": item.date.isoformat() if item.date else None,
        "location": item.location,
        "found": item.found,
        "status": item.status,
        "created_at": item.created_at.isoformat() if item.created_at else None
    }

def serialize_claim(claim: Claim) -> dict:
    """Convert Claim ORM object to dict"""
    return {
        "id": claim.id,
        "user_id": claim.user_id,
        "item_id": claim.item_id,
        "claim_message": claim.claim_message,
        "status": claim.status,
        "created_at": claim.created_at.isoformat() if claim.created_at else None
    }

# ---------------- Authentication Routes ----------------
@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # Check if email already exists
        if db.query(User).filter(User.email == user.email).first():
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "message": "Email already registered",
                    "data": None
                }
            )
        
        # Hash password and create user
        hashed_password = pwd_context.hash(user.password)
        new_user = User(
            role=user.role,
            fullname=user.fullname,
            email=user.email,
            field_of_study=user.field_of_study,
            year=user.year,
            password=hashed_password,
            created_at=datetime.utcnow()
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "User registered successfully",
                "data": {"user_id": new_user.id}
            }
        )
    except ValidationError as ve:
        return JSONResponse(
            status_code=422,
            content={
                "status": "failed",
                "message": f"Validation error: {str(ve)}",
                "data": None
            }
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Internal server error: {str(e)}",
                "data": None
            }
        )

@app.post("/login")
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == credentials.email).first()
        
        if not user:
            return JSONResponse(
                status_code=401,
                content={
                    "status": "failed",
                    "message": "Invalid email or password",
                    "data": None
                }
            )
        
        if not pwd_context.verify(credentials.password, user.password):
            return JSONResponse(
                status_code=401,
                content={
                    "status": "failed",
                    "message": "Invalid email or password",
                    "data": None
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Login successful",
                "data": {
                    "user_id": user.id,
                    "role": user.role,
                    "email": user.email,
                    "fullname": user.fullname,
                }
            }
        )
    except ValidationError as ve:
        return JSONResponse(
            status_code=422,
            content={
                "status": "failed",
                "message": f"Validation error: {str(ve)}",
                "data": None
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Internal server error: {str(e)}",
                "data": None
            }
        )

# ---------------- Lost Item Routes ----------------
@app.post("/items/add")
def add_lost_item(
    user_id: int = Form(...),
    item_type: str = Form(...),
    item_name: str = Form(...),
    item_description: str = Form(...),
    item_image: UploadFile = File(...),
    email: EmailStr = Form(...),
    location: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": "User not found",
                    "data": None
                }
            )
        
        # Validate item_type
        if item_type not in ["lost", "found"]:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "message": "Item type must be either 'lost' or 'found'",
                    "data": None
                }
            )
        
        # Validate item_name length
        if len(item_name) < 3 or len(item_name) > 100:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "message": "Item name must be between 3 and 100 characters",
                    "data": None
                }
            )
        
        # Validate item_description length
        if len(item_description) < 10 or len(item_description) > 500:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "message": "Item description must be between 10 and 500 characters",
                    "data": None
                }
            )
        
        # Validate location length
        if len(location) < 3 or len(location) > 100:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "message": "Location must be between 3 and 100 characters",
                    "data": None
                }
            )
        
        # Validate image file
        if not item_image.content_type.startswith('image/'):
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "message": "Uploaded file must be an image",
                    "data": None
                }
            )
        
        # Read image bytes
        image_bytes = item_image.file.read()
        
        # Validate image size (e.g., max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        if len(image_bytes) > max_size:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "message": "Image size must not exceed 5MB",
                    "data": None
                }
            )
        
        current_date = datetime.utcnow().date()
        
        # Save in database
        new_item = LostItem(
            user_id=user_id,
            item_type=item_type,
            item_name=item_name,
            item_description=item_description,
            item_image=image_bytes,
            email=email,
            date=current_date,
            location=location,
            found=False,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Item submitted successfully, awaiting admin approval",
                "data": {"item_id": new_item.id}
            }
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to add item: {str(e)}",
                "data": None
            }
        )

@app.post("/items/approve/{item_id}")
def approve_item(item_id: int, db: Session = Depends(get_db)):
    try:
        item = db.query(LostItem).filter(LostItem.id == item_id).first()
        if not item:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": "Item not found",
                    "data": None
                }
            )
        
        item.status = "approved"
        db.commit()
        db.refresh(item)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Item {item_id} approved successfully",
                "data": {"item_id": item.id, "status": item.status}
            }
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to approve item: {str(e)}",
                "data": None
            }
        )

@app.post("/items/reject/{item_id}")
def reject_item(item_id: int, db: Session = Depends(get_db)):
    try:
        item = db.query(LostItem).filter(LostItem.id == item_id).first()
        if not item:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": "Item not found",
                    "data": None
                }
            )
        
        item.status = "rejected"
        db.commit()
        db.refresh(item)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Item {item_id} rejected successfully",
                "data": {"item_id": item.id, "status": item.status}
            }
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to reject item: {str(e)}",
                "data": None
            }
        )

@app.get("/items/pending")
def get_pending_items(db: Session = Depends(get_db)):
    try:
        pending_items = db.query(LostItem).filter(LostItem.status == "pending").all()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Pending items retrieved successfully",
                "data": {
                    "pending_count": len(pending_items),
                    "items": [serialize_item(i) for i in pending_items]
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to retrieve pending items: {str(e)}",
                "data": None
            }
        )

@app.get("/items/approved")
def get_approved_items(db: Session = Depends(get_db)):
    try:
        approved_items = db.query(LostItem).filter(LostItem.status == "approved").all()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Approved items retrieved successfully",
                "data": {
                    "approved_count": len(approved_items),
                    "items": [serialize_item(i) for i in approved_items]
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to retrieve approved items: {str(e)}",
                "data": None
            }
        )

@app.get("/items/all")
def get_all_items(item_type: str = None, db: Session = Depends(get_db)):
    """
    Get all items, optionally filtered by item_type.
    - item_type='lost': Items that users have lost
    - item_type='found': Items that users have found
    - No item_type: Returns all items
    """
    try:
        query = db.query(LostItem)
        if item_type:
            # Validate item_type parameter
            if item_type not in ["lost", "found"]:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "failed",
                        "message": "Item type must be either 'lost' or 'found'",
                        "data": None
                    }
                )
            query = query.filter(LostItem.item_type == item_type)
        
        items = query.all()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Items retrieved successfully",
                "data": {
                    "count": len(items),
                    "items": [serialize_item(i) for i in items]
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to retrieve items: {str(e)}",
                "data": None
            }
        )

@app.get("/items/{item_id}")
def view_item(item_id: int, db: Session = Depends(get_db)):
    try:
        item = db.query(LostItem).filter(LostItem.id == item_id).first()
        if not item:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": "Item not found",
                    "data": None
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Item retrieved successfully",
                "data": serialize_item(item)
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to retrieve item: {str(e)}",
                "data": None
            }
        )

# ---------------- User-Specific Items ----------------
@app.get("/my-items/{user_id}")
def get_my_items(user_id: int, db: Session = Depends(get_db)):
    try:
        items = db.query(LostItem).filter(LostItem.user_id == user_id).all()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "User items retrieved successfully",
                "data": {
                    "count": len(items),
                    "items": [serialize_item(i) for i in items]
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to retrieve user items: {str(e)}",
                "data": None
            }
        )

@app.delete("/items/{item_id}")
def delete_item(item_id: int, user_id: int, db: Session = Depends(get_db)):
    try:
        item = db.query(LostItem).filter(LostItem.id == item_id, LostItem.user_id == user_id).first()
        if not item:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": "Item not found or unauthorized",
                    "data": None
                }
            )
        
        db.delete(item)
        db.commit()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Item {item_id} deleted successfully",
                "data": {"item_id": item_id}
            }
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to delete item: {str(e)}",
                "data": None
            }
        )

@app.put("/items/{item_id}/edit")
def edit_item(item_id: int, user_id: int, updated_item: LostItemUpdate, db: Session = Depends(get_db)):
    try:
        item = db.query(LostItem).filter(LostItem.id == item_id, LostItem.user_id == user_id).first()
        if not item:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": "Item not found or unauthorized",
                    "data": None
                }
            )
        
        # Use model_dump instead of dict (Pydantic v2)
        update_data = updated_item.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        
        db.commit()
        db.refresh(item)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Item {item_id} updated successfully",
                "data": serialize_item(item)
            }
        )
    except ValidationError as ve:
        return JSONResponse(
            status_code=422,
            content={
                "status": "failed",
                "message": f"Validation error: {str(ve)}",
                "data": None
            }
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to update item: {str(e)}",
                "data": None
            }
        )

@app.put("/items/{item_id}/found")
def mark_as_found(item_id: int, user_id: int, db: Session = Depends(get_db)):
    try:
        item = db.query(LostItem).filter(LostItem.id == item_id, LostItem.user_id == user_id).first()
        if not item:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": "Item not found or unauthorized",
                    "data": None
                }
            )
        
        if item.status != "approved":
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "message": "Only approved items can be marked as found",
                    "data": None
                }
            )
        
        item.found = True
        db.commit()
        db.refresh(item)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Item {item_id} marked as found",
                "data": serialize_item(item)
            }
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to mark item as found: {str(e)}",
                "data": None
            }
        )

# ---------------- Claim Routes ----------------

@app.post("/claim")
def claim_item(item_id: int, user_id: int, claim_message: str, db: Session = Depends(get_db)):
    try:
        # Step 1: Find the item
        item = db.query(LostItem).filter(LostItem.id == item_id).first()
        if not item:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": "Item not found",
                    "data": None
                }
            )

        # Step 2: Check if item is approved (regardless of type)
        if item.status != "approved":
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "message": "Items must be approved by admin before claiming",
                    "data": None
                }
            )

        # Step 3: Prevent users from claiming their own items
        if item.user_id == user_id:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "message": "You cannot claim your own item",
                    "data": None
                }
            )

        # Step 4: Check if user already has a pending claim for this item
        existing_claim = db.query(Claim).filter(
            Claim.user_id == user_id,
            Claim.item_id == item_id,
            Claim.status == "pending"
        ).first()
        
        if existing_claim:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "message": "You already have a pending claim for this item",
                    "data": None
                }
            )

        # Step 5: Validate claim message
        if not claim_message or len(claim_message.strip()) < 10:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "failed",
                    "message": "Claim message must be at least 10 characters",
                    "data": None
                }
            )

        # Step 6: Create a new claim
        claim = Claim(
            user_id=user_id,
            item_id=item_id,
            claim_message=claim_message.strip(),
            status="pending",
            created_at=datetime.utcnow()
        )
        db.add(claim)
        db.commit()
        db.refresh(claim)

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Claim submitted successfully",
                "data": {
                    "claim_id": claim.id,
                    "item_id": claim.item_id,
                    "status": claim.status
                }
            }
        )

    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to submit claim: {str(e)}",
                "data": None
            }
        )


@app.get("/claims/pending")
def get_pending_claims(db: Session = Depends(get_db)):
    try:
        pending_claims = db.query(Claim).filter(Claim.status == "pending").all()
        claims_with_details = []
        
        for claim in pending_claims:
            claims_with_details.append({
                "id": claim.id,
                "user_id": claim.user_id,
                "item_id": claim.item_id,
                "item_name": claim.item.item_name if claim.item else "N/A",
                "claim_message": claim.claim_message,
                "status": claim.status,
                "created_at": claim.created_at.isoformat() if claim.created_at else None
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Pending claims retrieved successfully",
                "data": {
                    "count": len(claims_with_details),
                    "claims": claims_with_details
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to retrieve pending claims: {str(e)}",
                "data": None
            }
        )

@app.put("/claims/{claim_id}/approve")
def approve_claim(claim_id: int, db: Session = Depends(get_db)):
    try:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": "Claim not found",
                    "data": None
                }
            )
        
        claim.status = "approved"
        db.commit()
        db.refresh(claim)
        
        # Send email to item finder (owner)
        email_sent = False
        try:
            item_owner_email = claim.item.user.email
            subject = f"Your found item '{claim.item.item_name}' has been claimed"
            body = (
                f"Hello {claim.item.user.first_name},<br><br>"
                f"Your found item <b>{claim.item.item_name}</b> has been claimed by "
                f"{claim.user.first_name} {claim.user.last_name}.<br><br>"
                f"<b>Message from claimer:</b> {claim.claim_message}<br><br>"
                "Please contact the claimer to arrange item return.<br><br>"
                "Regards,<br>CEP Lost & Found Team"
            )
            send_email(to_email=item_owner_email, subject=subject, body=body)
            email_sent = True
        except Exception as email_error:
            # Log email error but don't fail the approval
            print(f"Email sending failed: {str(email_error)}")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Claim {claim_id} approved" + (" and finder notified by email" if email_sent else " (email notification failed)"),
                "data": {
                    "claim_id": claim.id, 
                    "status": claim.status,
                    "email_sent": email_sent
                }
            }
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to approve claim: {str(e)}",
                "data": None
            }
        )

@app.put("/claims/{claim_id}/reject")
def reject_claim(claim_id: int, db: Session = Depends(get_db)):
    try:
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failed",
                    "message": "Claim not found",
                    "data": None
                }
            )
        
        claim.status = "rejected"
        db.commit()
        db.refresh(claim)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Claim {claim_id} rejected successfully",
                "data": {"claim_id": claim.id, "status": claim.status}
            }
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "message": f"Failed to reject claim: {str(e)}",
                "data": None
            }
        )

# ---------------- Root ----------------
@app.get("/")
def root():
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "CEP Lost & Found API is running!",
            "data": {"version": "1.0", "endpoints": "/docs"}
        }
    )
