package tn.esprit.awd.candidate.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import tn.esprit.awd.candidate.entity.Candidate;

public interface CandidateRepository extends JpaRepository<Candidate, Long> {

    boolean existsByEmailIgnoreCase(String email);

    boolean existsByEmailIgnoreCaseAndIdNot(String email, Long id);
}
