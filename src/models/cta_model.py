from src.extenstion import db

class CTAClickModel(db.Model):
    __tablename__ = 'cta_clicks'
    
    id = db.Column(db.Integer, primary_key=True)
    button_id = db.Column(db.String(255), unique=True, nullable=False)
    click_count = db.Column(db.Integer, default=0, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'buttonId': self.button_id,
            'clickCount': self.click_count
        }
