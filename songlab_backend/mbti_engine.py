"""
동적 MBTI 보컬 타입 분석 엔진
점수 기반으로 실시간 장점/단점 생성 및 정확한 타입 매칭
"""

import numpy as np
from typing import Dict, List, Tuple

class MBTIVocalEngine:
    """
    MBTI 보컬 타입 분석 및 동적 특성 생성 엔진
    """
    
    def __init__(self):
        # 각 축별 특성 정의
        self.axis_characteristics = {
            'brightness': {
                'positive': {'name': '밝은 톤', 'traits': ['경쾌한 느낌', '신나는 노래에 잘 어울림', '활발한 인상']},
                'negative': {'name': '깊은 톤', 'traits': ['진지한 느낌', '감정적인 곡에 강함', '성숙한 인상']}
            },
            'thickness': {
                'positive': {'name': '두꺼운 음색', 'traits': ['풍성한 음색', '임팩트가 강함', '존재감이 큼']},
                'negative': {'name': '얇은 음색', 'traits': ['고음에 유리', '섬세한 표현', '가벼운 느낌']}
            },
            'clarity': {
                'positive': {'name': '선명한 음색', 'traits': ['전달력이 좋음', '또렷한 발음', '집중도가 높음']},
                'negative': {'name': '개성적 음색', 'traits': ['독특한 매력', '감성적 표현', '예술적 감각']}
            },
            'power': {
                'positive': {'name': '강한 발성', 'traits': ['파워풀한 느낌', '다이나믹함', '압도적 가창력']},
                'negative': {'name': '부드러운 발성', 'traits': ['감미로운 느낌', '편안함을 줌', '안정적인 발성']}
            }
        }
        
        # 16가지 완전한 보컬 타입 정의
        self.vocal_types = self._initialize_vocal_types()
    
    def _initialize_vocal_types(self) -> Dict:
        """
        16가지 MBTI 보컬 타입 초기화
        """
        return {
            'DKCS': {
                'name': '카리스마틱 보컬',
                'desc': '깊고 도톰한 음색으로 강한 인상을 주는 타입',
                'genre_strength': ['Soul', 'R&B', 'Blues', 'Jazz'],
                'representative_artists': ['Adele', 'Amy Winehouse', 'Alicia Keys'],
                'base_songs': {
                    'female': ['Adele - Rolling in the Deep', 'Amy Winehouse - Rehab', 'Christina Aguilera - Beautiful'],
                    'male': ['Bruno Mars - When I Was Your Man', 'John Legend - All of Me', 'Ed Sheeran - Thinking Out Loud']
                }
            },
            'DKCW': {
                'name': '서정적 보컬',
                'desc': '따뜻하고 부드러운 음색의 감성적인 타입',
                'genre_strength': ['Ballad', 'Folk', 'Soft Pop'],
                'representative_artists': ['Norah Jones', 'Sade', 'Billie Eilish'],
                'base_songs': {
                    'female': ['Norah Jones - Come Away With Me', 'Sade - Smooth Operator', 'Billie Eilish - Ocean Eyes'],
                    'male': ['Sam Smith - Stay With Me', 'James Arthur - Say You Won\'t Let Go', 'Hozier - Take Me to Church']
                }
            },
            'DKRS': {
                'name': '개성적 파워보컬',
                'desc': '독특하고 강렬한 음색으로 강한 개성을 드러내는 타입',
                'genre_strength': ['Alternative Rock', 'Grunge', 'Alternative Pop'],
                'representative_artists': ['Janis Joplin', 'Pink', 'Alanis Morissette'],
                'base_songs': {
                    'female': ['Janis Joplin - Piece of My Heart', 'Pink - What\'s Up', 'Alanis Morissette - You Oughta Know'],
                    'male': ['Kurt Cobain - Smells Like Teen Spirit', 'Chris Cornell - Black Hole Sun', 'Eddie Vedder - Alive']
                }
            },
            'DKRW': {
                'name': '몽환적 보컬',
                'desc': '신비롭고 몽환적인 분위기를 연출하는 타입',
                'genre_strength': ['Dream Pop', 'Indie Pop', 'Alternative'],
                'representative_artists': ['Lana Del Rey', 'FKA twigs', 'Grimes'],
                'base_songs': {
                    'female': ['Lana Del Rey - Video Games', 'FKA twigs - Two Weeks', 'Grimes - Oblivion'],
                    'male': ['Bon Iver - Skinny Love', 'Thom Yorke - Hearing Damage', 'James Blake - Retrograde']
                }
            },
            'DNCS': {
                'name': '시크 보컬',
                'desc': '날카롭고 세련된 음색의 도시적인 타입',
                'genre_strength': ['Modern Pop', 'Electronic Pop', 'Urban'],
                'representative_artists': ['Rihanna', 'Dua Lipa', 'The Weeknd'],
                'base_songs': {
                    'female': ['Rihanna - Umbrella', 'Dua Lipa - Don\'t Start Now', 'Ariana Grande - positions'],
                    'male': ['The Weeknd - Can\'t Feel My Face', 'Zayn - Pillowtalk', 'Troye Sivan - Youth']
                }
            },
            'DNCW': {
                'name': '쿨 보컬',
                'desc': '차분하고 절제된 매력의 쿨한 타입',
                'genre_strength': ['Chill Pop', 'Neo Soul', 'Indie'],
                'representative_artists': ['Sade', 'Kings of Convenience', 'Norah Jones'],
                'base_songs': {
                    'female': ['Sade - No Ordinary Love', 'Norah Jones - Lonestar', 'Billie Eilish - lovely'],
                    'male': ['Kings of Convenience - I\'d Rather Dance With You', 'Jack Johnson - Better Together', 'Daniel Caesar - Best Part']
                }
            },
            'DNRS': {
                'name': '록 보컬',
                'desc': '날카로운 음색과 강한 에너지의 록 스타일',
                'genre_strength': ['Rock', 'Alternative Rock', 'Pop Rock'],
                'representative_artists': ['Joan Jett', 'Gwen Stefani', 'Shirley Manson'],
                'base_songs': {
                    'female': ['Joan Jett - Bad Reputation', 'Gwen Stefani - Just a Girl', 'Shirley Manson - Stupid Girl'],
                    'male': ['Green Day - Basket Case', 'Foo Fighters - Everlong', 'Red Hot Chili Peppers - Give It Away']
                }
            },
            'DNRW': {
                'name': '얼터너티브 보컬',
                'desc': '독특한 음색으로 개성을 추구하는 얼터너티브 타입',
                'genre_strength': ['Alternative', 'Indie Rock', 'Experimental'],
                'representative_artists': ['Radiohead', 'PJ Harvey', 'Cat Power'],
                'base_songs': {
                    'female': ['PJ Harvey - Down by the Water', 'Cat Power - The Greatest', 'Björk - Army of Me'],
                    'male': ['Radiohead - Creep', 'Modest Mouse - Float On', 'The Strokes - Last Nite']
                }
            },
            'BKCS': {
                'name': '디바 보컬',
                'desc': '화려하고 강력한 음색의 완벽한 디바 타입',
                'genre_strength': ['Pop', 'R&B', 'Gospel', 'Soul'],
                'representative_artists': ['Whitney Houston', 'Mariah Carey', 'Celine Dion'],
                'base_songs': {
                    'female': ['Whitney Houston - I Will Always Love You', 'Mariah Carey - Vision of Love', 'Celine Dion - My Heart Will Go On'],
                    'male': ['Luther Vandross - Never Too Much', 'John Legend - Ordinary People', 'Alicia Keys - If I Ain\'t Got You']
                }
            },
            'BKCW': {
                'name': '팝 보컬',
                'desc': '밝고 매력적인 음색의 대중적인 팝 보컬',
                'genre_strength': ['Pop', 'Dance Pop', 'Contemporary'],
                'representative_artists': ['Taylor Swift', 'Katy Perry', 'Ariana Grande'],
                'base_songs': {
                    'female': ['Taylor Swift - Love Story', 'Katy Perry - Roar', 'Ariana Grande - Thank U, Next'],
                    'male': ['Justin Timberlake - Can\'t Stop the Feeling', 'Ed Sheeran - Perfect', 'Bruno Mars - Count on Me']
                }
            },
            'BKRS': {
                'name': '소울 보컬',
                'desc': '감정이 풍부하고 깊이 있는 소울 음악 특화 타입',
                'genre_strength': ['Soul', 'Neo Soul', 'Gospel', 'Funk'],
                'representative_artists': ['Aretha Franklin', 'Alicia Keys', 'Amy Winehouse'],
                'base_songs': {
                    'female': ['Aretha Franklin - Respect', 'Alicia Keys - Fallin\'', 'Amy Winehouse - Valerie'],
                    'male': ['Stevie Wonder - Superstition', 'Marvin Gaye - What\'s Going On', 'John Legend - Used to Love U']
                }
            },
            'BKRW': {
                'name': '인디 보컬',
                'desc': '자유롭고 개성적인 인디 음악 스타일',
                'genre_strength': ['Indie Pop', 'Folk Pop', 'Alternative Pop'],
                'representative_artists': ['Regina Spektor', 'Feist', 'Yeah Yeah Yeahs'],
                'base_songs': {
                    'female': ['Regina Spektor - Fidelity', 'Feist - 1234', 'Yeah Yeah Yeahs - Heads Will Roll'],
                    'male': ['Vampire Weekend - A-Punk', 'Arctic Monkeys - Do I Wanna Know?', 'The National - Bloodbuzz Ohio']
                }
            },
            'BNCS': {
                'name': '댄스 보컬',
                'desc': '경쾌하고 리드미컬한 댄스 음악 특화 타입',
                'genre_strength': ['Dance Pop', 'EDM Pop', 'Electronic'],
                'representative_artists': ['Dua Lipa', 'Lady Gaga', 'Kylie Minogue'],
                'base_songs': {
                    'female': ['Dua Lipa - Physical', 'Lady Gaga - Just Dance', 'Kylie Minogue - Can\'t Get You Out of My Head'],
                    'male': ['Calvin Harris - Feel So Close', 'David Guetta - Titanium', 'Justin Timberlake - SexyBack']
                }
            },
            'BNCW': {
                'name': '어쿠스틱 보컬',
                'desc': '자연스럽고 편안한 어쿠스틱 음악 특화 타입',
                'genre_strength': ['Acoustic Pop', 'Folk', 'Singer-songwriter'],
                'representative_artists': ['Norah Jones', 'Colbie Caillat', 'Jason Mraz'],
                'base_songs': {
                    'female': ['Norah Jones - Don\'t Know Why', 'Colbie Caillat - Bubbly', 'Corinne Bailey Rae - Put Your Records On'],
                    'male': ['Jason Mraz - I\'m Yours', 'Jack Johnson - Banana Pancakes', 'John Mayer - Your Body Is a Wonderland']
                }
            },
            'BNRS': {
                'name': '펑크 보컬',
                'desc': '경쾌하고 펑키한 리듬의 펑크 스타일',
                'genre_strength': ['Funk', 'Neo-Funk', 'Funk Pop'],
                'representative_artists': ['Chaka Khan', 'Prince', 'OutKast'],
                'base_songs': {
                    'female': ['Chaka Khan - I\'m Every Woman', 'Lauryn Hill - Doo Wop (That Thing)', 'Erykah Badu - On & On'],
                    'male': ['Bruno Mars - Uptown Funk', 'Anderson .Paak - Come Down', 'Prince - Kiss']
                }
            },
            'BNRW': {
                'name': '실험적 보컬',
                'desc': '실험적이고 창의적인 음악적 도전을 즐기는 타입',
                'genre_strength': ['Experimental', 'Art Pop', 'Avant-garde'],
                'representative_artists': ['Björk', 'FKA twigs', 'Grimes'],
                'base_songs': {
                    'female': ['Björk - Army of Me', 'FKA twigs - Cellophane', 'Grimes - Genesis'],
                    'male': ['Thom Yorke - Black Swan', 'Bon Iver - Holocene', 'Sufjan Stevens - Chicago']
                }
            }
        }
    
    def analyze_mbti_type(self, scores: Dict, gender: str = 'unknown') -> Dict:
        """
        MBTI 점수 기반 보컬 타입 분석 및 동적 특성 생성
        """
        # 1. 타입 코드 결정
        type_code = self._determine_type_code(scores)
        
        # 2. 기본 타입 정보 가져오기
        base_type = self.vocal_types.get(type_code, self.vocal_types['BKCW'])
        
        # 3. 점수 기반 동적 특성 생성
        dynamic_traits = self._generate_dynamic_traits(scores)
        
        # 4. 성별 기반 곡 선택
        songs = self._select_songs_by_gender(base_type, gender)
        
        # 5. 최종 결과 구성
        result = {
            'type_code': type_code,
            'name': base_type['name'],
            'desc': base_type['desc'],
            'genre_strength': base_type['genre_strength'],
            'representative_artists': base_type['representative_artists'],
            'songs': songs,
            'pros': dynamic_traits['pros'],
            'cons': dynamic_traits['cons'],
            'characteristics': dynamic_traits['characteristics'],
            'improvement_suggestions': dynamic_traits['improvements']
        }
        
        return result
    
    def _determine_type_code(self, scores: Dict) -> str:
        """
        MBTI 점수 기반 4글자 타입 코드 결정
        """
        type_code = ''
        type_code += 'D' if scores['brightness'] < 0 else 'B'  # Deep vs Bright
        type_code += 'K' if scores['thickness'] > 0 else 'N'   # thicK vs thiN
        type_code += 'C' if scores['clarity'] > 0 else 'R'     # Clear vs Rough
        type_code += 'S' if scores['power'] > 0 else 'W'       # Strong vs Weak
        return type_code
    
    def _generate_dynamic_traits(self, scores: Dict) -> Dict:
        """
        점수 기반 동적 특성 생성 (장점, 단점, 특성, 개선사항)
        """
        pros = []
        cons = []
        characteristics = []
        improvements = []
        
        # 각 축별 분석
        for axis, score in scores.items():
            if axis not in self.axis_characteristics:
                continue
                
            axis_data = self.axis_characteristics[axis]
            
            # 점수 절댓값으로 강도 판단
            intensity = abs(score)
            
            if score > 0:  # Positive 방향
                trait_data = axis_data['positive']
                if intensity > 60:  # 강한 특성
                    pros.extend(trait_data['traits'][:2])  # 상위 2개 특성
                    characteristics.append(f"매우 {trait_data['name']}적 특성")
                elif intensity > 30:  # 중간 특성
                    pros.extend(trait_data['traits'][:1])  # 상위 1개 특성
                    characteristics.append(f"{trait_data['name']}적 경향")
                
                # 너무 극단적인 경우 단점도 추가
                if intensity > 80:
                    cons.append(f"지나치게 {trait_data['name']}하여 균형감 필요")
                    improvements.append(f"{axis_data['negative']['name']} 요소 보완 연습")
                    
            else:  # Negative 방향
                trait_data = axis_data['negative']
                if intensity > 60:  # 강한 특성
                    pros.extend(trait_data['traits'][:2])
                    characteristics.append(f"매우 {trait_data['name']}적 특성")
                elif intensity > 30:  # 중간 특성
                    pros.extend(trait_data['traits'][:1])
                    characteristics.append(f"{trait_data['name']}적 경향")
                
                # 너무 극단적인 경우 단점도 추가
                if intensity > 80:
                    cons.append(f"지나치게 {trait_data['name']}하여 다양성 부족")
                    improvements.append(f"{axis_data['positive']['name']} 요소 개발 필요")
        
        # 중간 범위 점수들 (균형잡힌 특성)
        balanced_axes = [axis for axis, score in scores.items() if abs(score) < 30]
        if balanced_axes:
            pros.append("균형잡힌 음성 특성")
            characteristics.append("다양한 장르 적응 가능")
        
        # 전체적인 개선사항 추가
        if len([score for score in scores.values() if abs(score) > 70]) > 2:
            improvements.append("극단적 특성의 균형감 개발")
            
        # 중복 제거 및 정리
        pros = list(set(pros))[:4]  # 최대 4개
        cons = list(set(cons))[:3]  # 최대 3개
        characteristics = list(set(characteristics))[:3]  # 최대 3개
        improvements = list(set(improvements))[:3]  # 최대 3개
        
        # 기본값 설정 (빈 리스트 방지)
        if not pros:
            pros = ["개성 있는 음색", "독특한 매력"]
        if not cons:
            cons = ["특정 장르에 제한적", "기술적 보완 필요"]
        if not characteristics:
            characteristics = ["개인만의 독특한 보컬 스타일"]
        if not improvements:
            improvements = ["다양한 발성 기법 연습", "음역대 확장 훈련"]
            
        return {
            'pros': pros,
            'cons': cons,
            'characteristics': characteristics,
            'improvements': improvements
        }
    
    def _select_songs_by_gender(self, base_type: Dict, gender: str) -> List[str]:
        """
        성별 기반 추천 곡 선택
        """
        base_songs = base_type['base_songs']
        
        if gender.lower() == 'female':
            return base_songs.get('female', base_songs.get('male', []))
        elif gender.lower() == 'male':
            return base_songs.get('male', base_songs.get('female', []))
        else:
            # 성별 불명 시 두 리스트 혼합
            female_songs = base_songs.get('female', [])
            male_songs = base_songs.get('male', [])
            mixed_songs = []
            
            # 번갈아가며 선택
            max_len = max(len(female_songs), len(male_songs))
            for i in range(max_len):
                if i < len(female_songs):
                    mixed_songs.append(female_songs[i])
                if i < len(male_songs):
                    mixed_songs.append(male_songs[i])
            
            return mixed_songs[:6]  # 최대 6곡
    
    def get_training_recommendations(self, scores: Dict, type_info: Dict) -> List[Dict]:
        """
        MBTI 점수 기반 훈련 추천 생성
        """
        recommendations = []
        
        # 각 축별 훈련 추천
        training_mapping = {
            'brightness': {
                'low': {'title': '음색 밝기 개발', 'description': '더 밝고 경쾌한 음색을 위한 훈련', 
                       'exercises': ['고음 발성 연습', '공명 위치 상승', '앞쪽 공명 강화']},
                'high': {'title': '음색 깊이 개발', 'description': '더 깊고 풍부한 음색을 위한 훈련',
                        'exercises': ['흉성 강화', '저음 발성 연습', '뒤쪽 공명 개발']}
            },
            'thickness': {
                'low': {'title': '음색 볼륨감 개발', 'description': '더 두껍고 풍성한 음색을 위한 훈련',
                       'exercises': ['복식호흡 강화', '성대접촉 개선', '공명강 확장']},
                'high': {'title': '음색 가벼움 개발', 'description': '더 가볍고 유연한 음색을 위한 훈련',
                        'exercises': ['두성 발성', '공명 조절', '호흡량 조절']}
            },
            'clarity': {
                'low': {'title': '음색 선명도 개선', 'description': '더 맑고 선명한 음색을 위한 훈련',
                       'exercises': ['발음 명료도 개선', '공명 정리', '음성위생 관리']},
                'high': {'title': '표현력 다양화', 'description': '더 다양한 음색 표현을 위한 훈련',
                        'exercises': ['음색 변화 연습', '감정 표현 기법', '창의적 해석']}
            },
            'power': {
                'low': {'title': '발성 파워 강화', 'description': '더 강력하고 임팩트 있는 발성 훈련',
                       'exercises': ['복식호흡 강화', '성대 근력 강화', '다이나믹 조절']},
                'high': {'title': '섬세한 표현 개발', 'description': '더 섬세하고 다양한 표현을 위한 훈련',
                        'exercises': ['마이크 테크닉', '다이나믹 조절', '감정 뉘앙스 표현']}
            }
        }
        
        for axis, score in scores.items():
            if axis not in training_mapping:
                continue
                
            if abs(score) > 40:  # 개선이 필요한 정도의 점수
                direction = 'high' if score > 40 else 'low'
                training_data = training_mapping[axis][direction]
                
                recommendations.append({
                    'category': axis,
                    'title': training_data['title'],
                    'description': training_data['description'],
                    'exercises': training_data['exercises'],
                    'priority': min(abs(score), 100) / 100  # 0-1 우선순위
                })
        
        # 우선순위 기준 정렬
        recommendations.sort(key=lambda x: x['priority'], reverse=True)
        
        # 기본 추천 (모든 보컬리스트에게 도움)
        basic_recommendations = [
            {
                'category': 'basic',
                'title': '기초 발성 훈련',
                'description': '모든 보컬리스트를 위한 기본 발성 연습',
                'exercises': ['복식호흡 연습', '발성 준비운동', '음계 연습'],
                'priority': 0.8
            }
        ]
        
        return recommendations[:3] + basic_recommendations  # 최대 4개 추천
    
    def calculate_compatibility_score(self, scores1: Dict, scores2: Dict) -> float:
        """
        두 보컬 타입 간 조화도 계산 (듀엣, 하모니 등에 활용)
        """
        total_diff = 0
        count = 0
        
        for axis in ['brightness', 'thickness', 'clarity', 'power']:
            if axis in scores1 and axis in scores2:
                # 차이가 클수록 낮은 조화도
                diff = abs(scores1[axis] - scores2[axis])
                # 반대 특성의 조화 (보완적 관계) 보너스
                if scores1[axis] * scores2[axis] < 0:  # 서로 다른 부호
                    diff *= 0.7  # 30% 보정
                total_diff += diff
                count += 1
        
        if count == 0:
            return 0.5
            
        # 0-100 스케일을 0-1로 변환하고 역수 취함
        avg_diff = total_diff / count
        compatibility = max(0, 1 - (avg_diff / 200))  # 200점 차이면 조화도 0
        
        return compatibility